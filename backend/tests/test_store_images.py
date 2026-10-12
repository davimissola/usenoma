from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Barrier
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.main import app
from app.modules.auth.security import create_access_token
from app.modules.stores import image_processing, storage
from app.modules.stores.models import Store, StoreImage, StoreImageVariant, StoreMember


def image_bytes(format='PNG', size=(640, 480)):
	buffer = BytesIO()

	with Image.new('RGB', size, 'red') as image:
		image.save(buffer, format=format)

	return buffer.getvalue()


def send_image(client, shop, image_type='logo', user='owner_id', data=None, mime_type='image/png'):
	if data is None:
		data = image_bytes()

	return client.put(f"/stores/{shop['store_id']}/images/{image_type}", files={'file': ('../../foto.jpg', data, mime_type)}, headers={'Authorization': f"Bearer {create_access_token(shop[user])}"})


@pytest.fixture
def storage_calls(monkeypatch):
	monkeypatch.setattr(settings, 'supabase_url', 'https://project.supabase.co')
	monkeypatch.setattr(settings, 'supabase_secret_key', SecretStr('sb_secret_apenas_para_testes'))
	monkeypatch.setattr(settings, 'supabase_storage_bucket', 'store-media')
	upload = Mock()
	delete = Mock()
	monkeypatch.setattr(storage, 'upload_store_image', upload)
	monkeypatch.setattr(storage, 'delete_store_image', delete)

	return upload, delete


@pytest.mark.parametrize('user', ['owner_id', 'manager_id'])
@pytest.mark.parametrize('format', ['JPEG', 'PNG', 'WEBP'])
def test_members_upload_allowed_formats_as_webp_variants_with_real_metadata(client, shop, storage_calls, user, format):
	upload, delete = storage_calls
	data = image_bytes(format)
	response = send_image(client, shop, user=user, data=data)

	assert response.status_code == 200
	result = response.json()
	assert result['store_id'] == str(shop['store_id'])
	assert result['type'] == 'logo'
	assert set(result['variants']) == {'small', 'medium'}
	assert 'storage_path' not in response.text
	assert 'sb_secret' not in response.text
	assert upload.call_count == 2
	delete.assert_not_called()
	uploaded = {call.args[0]: call.args[1] for call in upload.call_args_list}

	with SessionLocal() as db:
		for variant, expected_size in [('small', (256, 192)), ('medium', (512, 384))]:
			row = db.get(StoreImageVariant, (UUID(result['id']), variant))
			content = uploaded[row.storage_path]
			assert row.storage_path.startswith(f"stores/{shop['store_id']}/logo/")
			assert row.storage_path.endswith(f'/{variant}.webp')
			UUID(row.storage_path.split('/')[-2])
			assert row.mime_type == 'image/webp'
			assert (row.width, row.height, row.size_bytes) == (*expected_size, len(content))
			assert result['variants'][variant] == {'url': f'https://project.supabase.co/storage/v1/object/public/store-media/{row.storage_path}', 'mime_type': 'image/webp', 'width': row.width, 'height': row.height, 'size_bytes': row.size_bytes}

			with BytesIO(content) as buffer, Image.open(buffer) as decoded:
				decoded.load()
				assert decoded.format == 'WEBP'
				assert decoded.size == expected_size


@pytest.mark.parametrize('method', ['PUT', 'DELETE'])
def test_user_without_membership_is_denied_before_storage_call(client, shop, storage_calls, method):
	upload, delete = storage_calls
	# Até um arquivo inválido retorna 403: autorização ocorre antes de validar/processar.
	response = client.request(method, f"/stores/{shop['store_id']}/images/logo", files={'file': ('foto.png', b'arquivo invalido', 'image/png')}, headers={'Authorization': f"Bearer {create_access_token(shop['outsider_id'])}"})

	assert response.status_code == 403
	upload.assert_not_called()
	delete.assert_not_called()


@pytest.mark.parametrize('method', ['PUT', 'DELETE'])
def test_image_operations_require_authentication(client, shop, storage_calls, method):
	upload, delete = storage_calls
	response = client.request(method, f"/stores/{shop['store_id']}/images/logo", files={'file': ('foto.png', image_bytes(), 'image/png')})

	assert response.status_code == 401
	upload.assert_not_called()
	delete.assert_not_called()


@pytest.mark.parametrize('method', ['PUT', 'DELETE'])
def test_unknown_store_is_rejected_before_storage_call(client, shop, storage_calls, method):
	upload, delete = storage_calls
	response = client.request(method, f'/stores/{uuid4()}/images/logo', files={'file': ('foto.png', image_bytes(), 'image/png')}, headers={'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"})

	assert response.status_code == 404
	upload.assert_not_called()
	delete.assert_not_called()


@pytest.mark.parametrize('method', ['PUT', 'DELETE'])
def test_invalid_image_type_is_rejected(client, shop, storage_calls, method):
	upload, delete = storage_calls
	response = client.request(method, f"/stores/{shop['store_id']}/images/product", files={'file': ('foto.png', image_bytes(), 'image/png')}, headers={'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"})

	assert response.status_code == 422
	upload.assert_not_called()
	delete.assert_not_called()


@pytest.mark.parametrize('data, mime_type, status', [(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', 'image/svg+xml', 415), (b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', 'image/png', 422), (b'arquivo falso', 'image/png', 422), (b'', 'image/png', 422)])
def test_svg_and_invalid_files_are_rejected(client, shop, storage_calls, data, mime_type, status):
	upload, delete = storage_calls
	response = send_image(client, shop, data=data, mime_type=mime_type)

	assert response.status_code == status
	upload.assert_not_called()
	delete.assert_not_called()


def test_other_raster_formats_are_rejected(client, shop, storage_calls):
	upload, delete = storage_calls
	response = send_image(client, shop, data=image_bytes('GIF'), mime_type='image/gif')

	assert response.status_code == 415
	upload.assert_not_called()
	delete.assert_not_called()


def test_truncated_image_is_rejected(client, shop, storage_calls):
	upload, delete = storage_calls
	response = send_image(client, shop, data=image_bytes('JPEG')[:-20], mime_type='image/jpeg')

	assert response.status_code == 422
	upload.assert_not_called()
	delete.assert_not_called()


def test_oversized_file_is_rejected(client, shop, storage_calls):
	upload, delete = storage_calls
	response = send_image(client, shop, data=b'x' * (image_processing.MAX_IMAGE_BYTES + 1))

	assert response.status_code == 413
	upload.assert_not_called()
	delete.assert_not_called()


@pytest.mark.parametrize('size', [(6001, 1), (4500, 4500)])
def test_oversized_dimensions_and_pixel_count_are_rejected(client, shop, storage_calls, size):
	upload, delete = storage_calls
	response = send_image(client, shop, data=image_bytes(size=size))

	assert response.status_code == 413
	upload.assert_not_called()
	delete.assert_not_called()


def test_logo_and_cover_are_independent_and_replacement_removes_only_previous_logo(client, shop, storage_calls):
	upload, delete = storage_calls
	logo = send_image(client, shop).json()
	old_paths = {call.args[0] for call in upload.call_args_list}
	cover = send_image(client, shop, image_type='cover').json()
	new_logo = send_image(client, shop, data=image_bytes(size=(40, 30))).json()

	assert new_logo['id'] == logo['id']
	assert new_logo['variants']['medium']['url'] != logo['variants']['medium']['url']
	assert (new_logo['variants']['medium']['width'], new_logo['variants']['medium']['height']) == (40, 30)
	assert new_logo['variants']['small']['url'] == new_logo['variants']['medium']['url']
	assert {call.args[0] for call in delete.call_args_list} == old_paths
	assert upload.call_count == 4
	assert set(cover['variants']) == {'medium', 'large'}

	with SessionLocal() as db:
		assert db.scalar(select(func.count()).select_from(StoreImage)) == 2
		assert db.scalar(select(func.count()).select_from(StoreImageVariant)) == 4
		assert cover['variants']['large']['url'].endswith(db.get(StoreImageVariant, (UUID(cover['id']), 'large')).storage_path)
		assert new_logo['variants']['medium']['url'].endswith(db.get(StoreImageVariant, (UUID(new_logo['id']), 'medium')).storage_path)


def test_storage_failure_preserves_previous_reference_and_attempts_cleanup(client, shop, storage_calls):
	upload, delete = storage_calls
	previous = send_image(client, shop).json()
	previous_paths = {call.args[0] for call in upload.call_args_list}
	upload.reset_mock()
	upload.side_effect = HTTPException(status_code=503, detail='Storage indisponível.')
	response = send_image(client, shop)

	assert response.status_code == 503
	delete.assert_called_once_with(upload.call_args.args[0])

	with SessionLocal() as db:
		assert set(db.scalars(select(StoreImageVariant.storage_path).where(StoreImageVariant.store_image_id == UUID(previous['id'])))) == previous_paths


def test_database_constraint_failure_rolls_back_replacement_and_deletes_new_file(client, shop, storage_calls):
	upload, delete = storage_calls
	previous = send_image(client, shop).json()
	previous_paths = {call.args[0] for call in upload.call_args_list}
	upload.reset_mock()

	def invalidate_metadata(session, flush_context, instances):
		for item in session.new.union(session.dirty):
			if isinstance(item, StoreImageVariant):
				item.width = 0

	# Provoca uma rejeição real pelo CHECK do PostgreSQL, sem substituir o banco por um mock.
	event.listen(SessionLocal.class_, 'before_flush', invalidate_metadata)

	try:
		response = send_image(client, shop)
	finally:
		event.remove(SessionLocal.class_, 'before_flush', invalidate_metadata)

	assert response.status_code == 503
	assert {call.args[0] for call in delete.call_args_list} == {call.args[0] for call in upload.call_args_list}

	with SessionLocal() as db:
		assert set(db.scalars(select(StoreImageVariant.storage_path).where(StoreImageVariant.store_image_id == UUID(previous['id'])))) == previous_paths


def test_uncertain_commit_keeps_new_file_and_logs_without_private_exception(client, shop, storage_calls, caplog):
	upload, delete = storage_calls

	def lose_commit_response(connection):
		raise OperationalError(None, None, RuntimeError('sb_secret_dado_privado_da_excecao'))

	event.listen(engine, 'commit', lose_commit_response)

	try:
		response = send_image(client, shop)
	finally:
		event.remove(engine, 'commit', lose_commit_response)

	assert response.status_code == 503
	delete.assert_not_called()
	assert 'commit de imagem incerto' in caplog.text
	assert upload.call_args.args[0] in caplog.text
	assert 'sb_secret' not in caplog.text
	assert 'sb_secret' not in response.text


def test_failed_old_file_cleanup_does_not_break_new_image(client, shop, storage_calls, caplog):
	upload, delete = storage_calls
	previous = send_image(client, shop).json()
	previous_paths = {call.args[0] for call in upload.call_args_list}
	delete.side_effect = HTTPException(status_code=503, detail='sb_secret_erro_privado')
	response = send_image(client, shop)

	assert response.status_code == 200
	assert {call.args[0] for call in delete.call_args_list} == previous_paths
	assert all(path in caplog.text for path in previous_paths)
	assert 'sb_secret' not in caplog.text

	with SessionLocal() as db:
		assert response.json()['variants']['medium']['url'].endswith(db.get(StoreImageVariant, (UUID(previous['id']), 'medium')).storage_path)


def test_membership_revoked_during_upload_is_checked_again_and_new_file_is_removed(client, shop, storage_calls):
	upload, delete = storage_calls

	def revoke_during_upload(storage_path, data, mime_type):
		with SessionLocal() as db:
			member = db.get(StoreMember, (shop['store_id'], shop['manager_id']))

			if member:
				db.delete(member)
				db.commit()

	upload.side_effect = revoke_during_upload
	response = send_image(client, shop, user='manager_id')

	assert response.status_code == 403
	assert {call.args[0] for call in delete.call_args_list} == {call.args[0] for call in upload.call_args_list}

	with SessionLocal() as db:
		assert db.scalar(select(func.count()).select_from(StoreImage)) == 0


def test_upload_and_cleanup_do_not_hold_store_lock(client, shop, storage_calls):
	upload, delete = storage_calls

	def inspect_database(*args):
		with SessionLocal() as db:
			db.connection().exec_driver_sql("SET LOCAL lock_timeout = '500ms'")
			db.execute(select(Store).where(Store.id == shop['store_id']).with_for_update())
			assert db.scalar(select(func.count()).select_from(StoreImage)) in {0, 1}

	upload.side_effect = inspect_database
	delete.side_effect = inspect_database
	assert send_image(client, shop).status_code == 200
	assert send_image(client, shop).status_code == 200


def test_simultaneous_replacements_keep_one_reference_and_remove_superseded_paths(client, shop, storage_calls):
	upload, delete = storage_calls
	previous = send_image(client, shop).json()
	previous_paths = {call.args[0] for call in upload.call_args_list}
	upload.reset_mock()
	barrier = Barrier(2)

	def wait_for_both_uploads(storage_path, data, mime_type):
		barrier.wait(timeout=5)

	upload.side_effect = wait_for_both_uploads

	def replace(user):
		with TestClient(app, base_url='https://api.noma.test') as concurrent_client:
			return send_image(concurrent_client, shop, user=user)

	with ThreadPoolExecutor(max_workers=2) as executor:
		responses = list(executor.map(replace, ['owner_id', 'manager_id']))

	assert [response.status_code for response in responses] == [200, 200]
	new_paths = {call.args[0] for call in upload.call_args_list}
	assert len(new_paths) == 4

	with SessionLocal() as db:
		current_paths = set(db.scalars(select(StoreImageVariant.storage_path).where(StoreImageVariant.store_image_id == UUID(previous['id']))))
		assert current_paths <= new_paths
		assert len(current_paths) == 2
		assert db.scalar(select(func.count()).select_from(StoreImage)) == 1

	removed_paths = {call.args[0] for call in delete.call_args_list}
	assert removed_paths == previous_paths | (new_paths - current_paths)


@pytest.mark.parametrize('user', ['owner_id', 'manager_id'])
def test_member_can_remove_image_and_repeated_delete_is_idempotent(client, shop, storage_calls, user):
	upload, delete = storage_calls
	previous = send_image(client, shop).json()
	previous_paths = {call.args[0] for call in upload.call_args_list}
	path = f"/stores/{shop['store_id']}/images/logo"
	headers = {'Authorization': f"Bearer {create_access_token(shop[user])}"}

	assert client.delete(path, headers=headers).status_code == 204
	assert client.delete(path, headers=headers).status_code == 204
	assert {call.args[0] for call in delete.call_args_list} == previous_paths

	with SessionLocal() as db:
		assert db.scalar(select(func.count()).select_from(StoreImage)) == 0
		assert db.scalar(select(func.count()).select_from(StoreImageVariant)) == 0


def test_delete_cleanup_failure_is_logged_after_reference_is_removed(client, shop, storage_calls, caplog):
	upload, delete = storage_calls
	previous = send_image(client, shop).json()
	previous_paths = {call.args[0] for call in upload.call_args_list}
	delete.side_effect = HTTPException(status_code=503, detail='Falha externa.')
	response = client.delete(f"/stores/{shop['store_id']}/images/logo", headers={'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"})

	assert response.status_code == 204
	assert all(path in caplog.text for path in previous_paths)

	with SessionLocal() as db:
		assert db.scalar(select(func.count()).select_from(StoreImage)) == 0


def test_image_constraints_and_store_delete_cascade(shop):
	data = {'store_id': shop['store_id'], 'type': 'logo'}

	with SessionLocal() as db:
		image = StoreImage(**data)
		db.add(image)
		db.flush()
		db.add(StoreImageVariant(store_image_id=image.id, variant='medium', storage_path='stores/test/medium.webp', mime_type='image/webp', width=32, height=24, size_bytes=100))
		db.commit()
		db.add(StoreImage(**data))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'uq_store_images_store_type'
		db.delete(db.get(Store, shop['store_id']))
		db.commit()
		assert db.scalar(select(func.count()).select_from(StoreImage)) == 0
		assert db.scalar(select(func.count()).select_from(StoreImageVariant)) == 0


def test_browser_preflight_allows_put(client, shop):
	response = client.options(f"/stores/{shop['store_id']}/images/logo", headers={'Origin': 'https://noma.test', 'Access-Control-Request-Method': 'PUT', 'Access-Control-Request-Headers': 'authorization,content-type'})

	assert response.status_code == 200
	assert 'PUT' in response.headers['access-control-allow-methods']


@pytest.mark.parametrize('field, value, constraint', [('type', 'other', 'ck_store_images_type'), ('mime_type', 'image/svg+xml', 'ck_store_image_variants_mime_type'), ('storage_path', '', 'ck_store_image_variants_storage_path'), ('width', 0, 'ck_store_image_variants_metadata'), ('height', -1, 'ck_store_image_variants_metadata'), ('size_bytes', 0, 'ck_store_image_variants_metadata'), ('store_id', uuid4(), 'fk_store_images_store_id')])
def test_invalid_image_records_are_rejected_by_postgresql(shop, field, value, constraint):
	with SessionLocal() as db:
		if field in {'type', 'store_id'}:
			data = {'store_id': shop['store_id'], 'type': 'logo'}
			data[field] = value
			db.add(StoreImage(**data))
		else:
			image = StoreImage(store_id=shop['store_id'], type='logo')
			db.add(image)
			db.flush()
			data = {'store_image_id': image.id, 'variant': 'medium', 'storage_path': 'stores/test/medium.webp', 'mime_type': 'image/webp', 'width': 32, 'height': 24, 'size_bytes': 100}
			data[field] = value
			db.add(StoreImageVariant(**data))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == constraint


def test_failure_on_second_variant_upload_cleans_both_attempted_files(client, shop, storage_calls):
	upload, delete = storage_calls
	upload.side_effect = [None, HTTPException(status_code=503, detail='Segundo envio falhou.')]
	response = send_image(client, shop)

	assert response.status_code == 503
	assert upload.call_count == 2
	assert {call.args[0] for call in delete.call_args_list} == {call.args[0] for call in upload.call_args_list}

	with SessionLocal() as db:
		assert db.scalar(select(func.count()).select_from(StoreImage)) == 0
		assert db.scalar(select(func.count()).select_from(StoreImageVariant)) == 0


def test_small_image_uploads_one_physical_file_and_deletes_it_once(client, shop, storage_calls):
	upload, delete = storage_calls
	response = send_image(client, shop, data=image_bytes(size=(80, 40)))

	assert response.status_code == 200
	assert response.json()['variants']['small'] == response.json()['variants']['medium']
	upload.assert_called_once()
	assert client.delete(f"/stores/{shop['store_id']}/images/logo", headers={'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"}).status_code == 204
	delete.assert_called_once_with(upload.call_args.args[0])


def test_variant_name_is_unique_within_image_and_delete_image_cascades(shop):
	with SessionLocal() as db:
		image = StoreImage(store_id=shop['store_id'], type='logo')
		db.add(image)
		db.flush()
		image_id = image.id
		data = {'store_image_id': image_id, 'variant': 'small', 'storage_path': 'stores/test/small.webp', 'mime_type': 'image/webp', 'width': 256, 'height': 128, 'size_bytes': 100}
		db.add(StoreImageVariant(**data))
		db.commit()

	with SessionLocal() as db:
		db.add(StoreImageVariant(**data))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'store_image_variants_pkey'
		db.delete(db.get(StoreImage, image_id))
		db.commit()
		assert db.scalar(select(func.count()).select_from(StoreImageVariant)) == 0


@pytest.mark.parametrize('field, value, constraint', [('variant', 'other', 'ck_store_image_variants_variant'), ('store_image_id', uuid4(), 'fk_store_image_variants_image_id')])
def test_variant_name_and_parent_are_checked_by_postgresql(shop, field, value, constraint):
	with SessionLocal() as db:
		image = StoreImage(store_id=shop['store_id'], type='logo')
		db.add(image)
		db.flush()
		data = {'store_image_id': image.id, 'variant': 'small', 'storage_path': 'stores/test/small.webp', 'mime_type': 'image/webp', 'width': 256, 'height': 128, 'size_bytes': 100}
		data[field] = value
		db.add(StoreImageVariant(**data))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == constraint

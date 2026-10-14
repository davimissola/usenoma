from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from io import BytesIO
from threading import Barrier
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.database import SessionLocal
from app.main import app
from app.modules.auth.security import create_access_token
from app.modules.products import image_service, storage
from app.modules.products.models import Product, ProductImage, ProductSize
from app.modules.stores.models import StoreMember


def image_bytes(format='PNG', size=(2000, 1000)):
	with BytesIO() as buffer, Image.new('RGB', size, 'red') as image:
		image.save(buffer, format=format)
		return buffer.getvalue()


def send_image(client, shop, product, user='owner_id', data=None, image_id=None):
	method = 'POST'
	path = f"/stores/{shop['store_id']}/products/{product}/images"

	if image_id:
		method = 'PUT'
		path += f'/{image_id}'

	if data is None:
		data = image_bytes()

	return client.request(method, path, files={'file': ('../../foto.png', data, 'image/png')}, headers={'Authorization': f"Bearer {create_access_token(shop[user])}"})


@pytest.mark.parametrize('user', ['owner_id', 'manager_id'])
@pytest.mark.parametrize('format', ['JPEG', 'PNG', 'WEBP'])
def test_members_upload_only_webp_product_variants(client, shop, product, product_storage, user, format):
	upload, delete = product_storage
	response = send_image(client, shop, product, user=user, data=image_bytes(format))
	assert response.status_code == 201
	data = response.json()
	assert data['position'] == 1
	assert set(data['variants']) == {'card', 'large'}
	assert 'storage_path' not in response.text
	assert upload.call_count == 2
	delete.assert_not_called()

	with SessionLocal() as db:
		row = db.get(ProductImage, UUID(data['id']))
		assert row.product_id == product
		assert row.storage_path.startswith(f"stores/{shop['store_id']}/products/{product}/")
		assert row.storage_path.endswith('/large.webp')
		UUID(row.storage_path.split('/')[-2])

	for call, dimensions in zip(upload.call_args_list, [(800, 400), (1600, 800)]):
		assert call.args[2] == 'image/webp'
		with BytesIO(call.args[1]) as buffer, Image.open(buffer) as image:
			image.load()
			assert image.format == 'WEBP'
			assert image.size == dimensions


@pytest.mark.parametrize('method, suffix, data', [('POST', '', None), ('PUT', '/{image}', None), ('DELETE', '/{image}', None), ('PATCH', '/order', {'image_ids': []})])
@pytest.mark.parametrize('user, status', [(None, 401), ('outsider_id', 403)])
def test_image_operations_require_membership_before_processing(client, shop, product, product_storage, monkeypatch, method, suffix, data, user, status):
	process = Mock(side_effect=AssertionError('Usuário não autorizado não deve processar imagens.'))
	monkeypatch.setattr(image_service, 'process_image', process)
	headers = {}

	if user:
		headers = {'Authorization': f"Bearer {create_access_token(shop[user])}"}

	path = f"/stores/{shop['store_id']}/products/{product}/images{suffix.format(image=uuid4())}"
	if method in {'POST', 'PUT'}:
		response = client.request(method, path, files={'file': ('invalid.png', b'invalid', 'image/png')}, headers=headers)
	else:
		response = client.request(method, path, json=data, headers=headers)
	assert response.status_code == status
	process.assert_not_called()
	product_storage[0].assert_not_called()
	product_storage[1].assert_not_called()


@pytest.mark.parametrize('data, status', [(b'<svg xmlns="http://www.w3.org/2000/svg"/>', 422), (b'invalid', 422), (b'x' * (5 * 1024 * 1024 + 1), 413)], ids=['svg', 'invalid', 'oversized'])
def test_invalid_product_files_are_rejected_without_upload(client, shop, product, product_storage, data, status):
	assert send_image(client, shop, product, data=data).status_code == status
	product_storage[0].assert_not_called()


def test_processing_failure_does_not_upload(client, shop, product, product_storage, monkeypatch):
	monkeypatch.setattr(image_service, 'process_image', Mock(side_effect=HTTPException(status_code=422, detail='Falha de processamento.')))
	assert send_image(client, shop, product).status_code == 422
	product_storage[0].assert_not_called()


def test_svg_mime_and_oversized_resolution_are_rejected(client, shop, product, product_storage):
	path = f"/stores/{shop['store_id']}/products/{product}/images"
	headers = {'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"}
	assert client.post(path, files={'file': ('image.svg', b'<svg/>', 'image/svg+xml')}, headers=headers).status_code == 415
	assert send_image(client, shop, product, data=image_bytes(size=(6001, 1))).status_code == 413
	product_storage[0].assert_not_called()


@pytest.mark.parametrize('method', ['PUT', 'DELETE'])
def test_image_from_another_product_cannot_be_changed(client, shop, product, product_storage, method):
	with SessionLocal() as db:
		other = Product(store_id=shop['store_id'], name='Outro produto', price=Decimal('10.00'))
		db.add(other)
		db.flush()
		image = ProductImage(product_id=other.id, storage_path=f'products/{other.id}/large.webp', position=1)
		db.add(image)
		db.commit()
		image_id = image.id

	path = f"/stores/{shop['store_id']}/products/{product}/images/{image_id}"
	response = client.request(method, path, files={'file': ('image.png', image_bytes(), 'image/png')}, headers={'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"})
	assert response.status_code == 404
	product_storage[0].assert_not_called()
	product_storage[1].assert_not_called()
	with SessionLocal() as db:
		assert db.get(ProductImage, image_id) is not None


def test_full_product_rejects_new_image_before_processing(client, shop, product, product_storage, monkeypatch):
	with SessionLocal() as db:
		db.add_all([ProductImage(product_id=product, position=position, storage_path=f'products/{position}/large.webp') for position in range(1, 6)])
		db.commit()

	process = Mock(side_effect=AssertionError('Produto cheio não deve processar outra imagem.'))
	monkeypatch.setattr(image_service, 'process_image', process)
	assert send_image(client, shop, product, data=b'invalid').status_code == 409
	process.assert_not_called()
	product_storage[0].assert_not_called()


def test_failed_second_upload_cleans_new_files_without_saving_reference(client, shop, product, product_storage):
	upload, delete = product_storage
	upload.side_effect = [None, HTTPException(status_code=503, detail='Storage indisponível.')]
	assert send_image(client, shop, product).status_code == 503
	assert {call.args[0] for call in delete.call_args_list} == {call.args[0] for call in upload.call_args_list}

	with SessionLocal() as db:
		assert db.scalars(select(ProductImage)).all() == []


def test_confirmed_database_failure_cleans_all_new_variants(client, shop, product, product_storage, monkeypatch):
	original_commit = SessionLocal.class_.commit

	def fail_image_commit(db):
		if any(isinstance(item, ProductImage) for item in db.identity_map.values()):
			raise IntegrityError('commit', {}, Exception('falha confirmada'))
		return original_commit(db)

	monkeypatch.setattr(SessionLocal.class_, 'commit', fail_image_commit)
	assert send_image(client, shop, product).status_code == 503
	assert product_storage[0].call_count == 2
	assert product_storage[1].call_count == 2

	with SessionLocal() as db:
		assert db.scalars(select(ProductImage)).all() == []


def test_uncertain_commit_preserves_new_files(client, shop, product, product_storage, monkeypatch, caplog):
	original_commit = SessionLocal.class_.commit

	def lose_commit_response(db):
		image_write = any(isinstance(item, ProductImage) for item in db.identity_map.values())
		original_commit(db)

		if image_write:
			raise OperationalError('commit', {}, Exception('resposta perdida'))

	monkeypatch.setattr(SessionLocal.class_, 'commit', lose_commit_response)
	assert send_image(client, shop, product).status_code == 503
	product_storage[1].assert_not_called()
	assert 'arquivos preservados' in caplog.text

	with SessionLocal() as db:
		assert len(db.scalars(select(ProductImage)).all()) == 1


def test_replace_keeps_id_position_and_removes_old_variants_after_commit(client, shop, product, product_storage):
	upload, delete = product_storage
	first = send_image(client, shop, product).json()
	old_paths = [call.args[0] for call in upload.call_args_list]
	upload.reset_mock()
	response = send_image(client, shop, product, image_id=first['id'])
	assert response.status_code == 200
	assert response.json()['id'] == first['id']
	assert response.json()['position'] == first['position']
	assert response.json()['variants'] != first['variants']
	assert {call.args[0] for call in delete.call_args_list} == set(old_paths)
	assert not set(old_paths) & {call.args[0] for call in upload.call_args_list}


def test_failed_old_cleanup_does_not_invalidate_replacement(client, shop, product, product_storage, caplog):
	first = send_image(client, shop, product).json()
	product_storage[1].side_effect = HTTPException(status_code=503, detail='Não foi possível limpar.')
	response = send_image(client, shop, product, image_id=first['id'])
	assert response.status_code == 200
	assert client.get(f'/products/{product}').json()['images'][0] == response.json()
	assert 'arquivo pendente' in caplog.text


def test_reorder_updates_positions_and_delete_compacts_them(client, shop, product, product_storage):
	images = [send_image(client, shop, product).json() for _ in range(3)]
	base = f"/stores/{shop['store_id']}/products/{product}/images"
	headers = {'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"}
	ids = [images[2]['id'], images[0]['id'], images[1]['id']]
	product_storage[0].reset_mock()
	response = client.patch(f'{base}/order', json={'image_ids': ids}, headers=headers)
	assert response.status_code == 200
	assert [row['id'] for row in response.json()] == ids
	assert [row['position'] for row in response.json()] == [1, 2, 3]
	product_storage[0].assert_not_called()
	assert client.delete(f"{base}/{images[0]['id']}", headers=headers).status_code == 204
	public = client.get(f'/products/{product}').json()['images']
	assert [row['id'] for row in public] == [ids[0], ids[2]]
	assert [row['position'] for row in public] == [1, 2]
	assert product_storage[1].call_count == 2


@pytest.mark.parametrize('kind', ['repeated', 'missing', 'foreign'])
def test_invalid_reorder_preserves_existing_positions(client, shop, product, product_storage, kind):
	image = send_image(client, shop, product).json()
	ids = []

	if kind == 'repeated':
		ids = [image['id'], image['id']]
	elif kind == 'foreign':
		ids = [str(uuid4())]

	response = client.patch(f"/stores/{shop['store_id']}/products/{product}/images/order", json={'image_ids': ids}, headers={'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"})
	assert response.status_code == 422
	assert client.get(f'/products/{product}').json()['images'] == [image]
	product_storage[1].assert_not_called()


def test_product_delete_cascades_and_cleans_physical_variants(client, shop, product, product_storage):
	image = send_image(client, shop, product).json()
	with SessionLocal() as db:
		db.add(ProductSize(product_id=product, size='M', available=False))
		db.commit()

	response = client.delete(f"/stores/{shop['store_id']}/products/{product}", headers={'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"})
	assert response.status_code == 204
	assert product_storage[1].call_count == 2

	with SessionLocal() as db:
		assert db.get(Product, product) is None
		assert db.get(ProductImage, UUID(image['id'])) is None
		assert db.get(ProductSize, (product, 'M')) is None


def test_permission_revoked_during_upload_is_checked_again(client, shop, product, product_storage):
	def revoke_on_upload(path, data, mime):
		with SessionLocal() as db:
			member = db.get(StoreMember, (shop['store_id'], shop['manager_id']))

			if member:
				db.delete(member)
				db.commit()

	product_storage[0].side_effect = revoke_on_upload
	assert send_image(client, shop, product, user='manager_id').status_code == 403
	assert product_storage[1].call_count == 2


def test_simultaneous_uploads_do_not_exceed_five_images(shop, product, product_storage, monkeypatch):
	with SessionLocal() as db:
		db.add_all([ProductImage(product_id=product, position=position, storage_path=f'products/{position}/large.webp') for position in range(1, 5)])
		db.commit()

	barrier = Barrier(2)
	original_process = image_service.process_image

	def wait_for_both_uploads(data):
		barrier.wait(timeout=10)
		return original_process(data)

	monkeypatch.setattr(image_service, 'process_image', wait_for_both_uploads)

	def upload_once():
		with TestClient(app, base_url='https://api.noma.test') as client:
			return send_image(client, shop, product).status_code

	with ThreadPoolExecutor(max_workers=2) as executor:
		statuses = list(executor.map(lambda _: upload_once(), range(2)))

	assert sorted(statuses) == [201, 409]
	assert product_storage[1].call_count == 2
	with SessionLocal() as db:
		assert len(db.scalars(select(ProductImage).where(ProductImage.product_id == product)).all()) == 5

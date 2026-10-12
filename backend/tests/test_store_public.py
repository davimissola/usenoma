from unittest.mock import Mock

import pytest
from sqlalchemy import event, select

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.modules.auth.security import create_access_token
from app.modules.stores import storage
from app.modules.stores.models import StoreImage, StoreImageVariant


@pytest.fixture(autouse=True)
def public_storage(monkeypatch):
	monkeypatch.setattr(settings, 'supabase_url', 'https://public-project.supabase.co')
	monkeypatch.setattr(settings, 'supabase_storage_bucket', 'store-public-test')
	monkeypatch.setattr(settings, 'supabase_secret_key', None)
	request = Mock(side_effect=AssertionError('Leitura pública não deve acessar o Supabase Storage.'))

	for method in ['get', 'post', 'request']:
		monkeypatch.setattr(storage.httpx, method, request)

	yield

	request.assert_not_called()


def save_image(store_id, image_type, variants, mime_type='image/webp'):
	extensions = {'image/webp': 'webp', 'image/png': 'png', 'image/jpeg': 'jpg'}
	response_variants = {}

	with SessionLocal() as db:
		image = StoreImage(store_id=store_id, type=image_type)
		db.add(image)
		db.flush()

		for variant, (width, height) in variants.items():
			path = f'stores/{store_id}/{image_type}/teste/{variant}.{extensions[mime_type]}'
			db.add(StoreImageVariant(store_image_id=image.id, variant=variant, storage_path=path, mime_type=mime_type, width=width, height=height, size_bytes=1234))
			response_variants[variant] = {'url': f'https://public-project.supabase.co/storage/v1/object/public/store-public-test/{path}', 'mime_type': mime_type, 'width': width, 'height': height, 'size_bytes': 1234}

		db.commit()

	return response_variants


@pytest.mark.parametrize('image_types', [[], ['logo'], ['cover'], ['logo', 'cover']])
def test_public_store_returns_available_images_without_authentication(client, shop, image_types):
	expected = {'id': str(shop['store_id']), 'name': 'Saint', 'slug': 'saint', 'description': 'Streetwear.', 'logo': None, 'cover': None}
	presets = {'logo': {'small': (256, 128), 'medium': (512, 256)}, 'cover': {'medium': (960, 480), 'large': (1920, 960)}}

	for image_type in image_types:
		expected[image_type] = save_image(shop['store_id'], image_type, presets[image_type])

	response = client.get('/stores/slug/saint')

	assert response.status_code == 200
	assert response.json() == expected
	assert 'storage_path' not in response.text
	assert 'sb_secret' not in response.text
	assert not {'members', 'user_id', 'user_ids', 'role', 'roles', 'email', 'password_hash'} & response.json().keys()
	assert str(shop['owner_id']) not in response.text
	assert str(shop['manager_id']) not in response.text
	assert 'owner@example.com' not in response.text
	assert 'hash-de-teste' not in response.text


@pytest.mark.parametrize('image_type, variant, mime_type', [('logo', 'medium', 'image/png'), ('cover', 'large', 'image/jpeg')])
def test_public_store_preserves_legacy_image_with_only_one_variant(client, shop, image_type, variant, mime_type):
	expected = save_image(shop['store_id'], image_type, {variant: (600, 400)}, mime_type)
	response = client.get('/stores/slug/saint')

	assert response.status_code == 200
	assert response.json()[image_type] == expected
	assert set(response.json()[image_type]) == {variant}


def test_public_store_images_are_isolated_between_stores(client, shop):
	logo = save_image(shop['store_id'], 'logo', {'medium': (512, 256)})
	cover = save_image(shop['other_store_id'], 'cover', {'large': (1920, 960)})
	saint = client.get('/stores/slug/saint')
	noma = client.get('/stores/slug/noma-brasil')

	assert saint.status_code == 200
	assert noma.status_code == 200
	assert saint.json()['logo'] == logo
	assert saint.json()['cover'] is None
	assert noma.json()['logo'] is None
	assert noma.json()['cover'] == cover
	assert noma.json()['description'] is None
	assert str(shop['other_store_id']) not in saint.text
	assert str(shop['store_id']) not in noma.text


def test_public_store_unknown_slug_returns_not_found(client):
	response = client.get('/stores/slug/inexistente')

	assert response.status_code == 404
	assert response.json() == {'detail': 'Loja não encontrada.'}


def test_public_store_without_images_does_not_require_storage_configuration(client, shop, monkeypatch):
	monkeypatch.setattr(settings, 'supabase_url', None)
	response = client.get('/stores/slug/saint')

	assert response.status_code == 200
	assert response.json()['logo'] is None
	assert response.json()['cover'] is None


def test_public_store_with_images_rejects_missing_url(client, shop, monkeypatch):
	save_image(shop['store_id'], 'logo', {'medium': (512, 256)})
	monkeypatch.setattr(settings, 'supabase_url', None)
	response = client.get('/stores/slug/saint')

	assert response.status_code == 503
	assert response.json() == {'detail': 'Storage não configurado.'}


def test_public_store_read_does_not_add_queries_per_variant(client, shop):
	save_image(shop['store_id'], 'logo', {'medium': (512, 256)})
	queries = []

	def record_query(connection, cursor, statement, parameters, context, executemany):
		if statement.lstrip().upper().startswith('SELECT'):
			queries.append(statement)

	event.listen(engine, 'before_cursor_execute', record_query)

	try:
		first = client.get('/stores/slug/saint')
		first_count = len(queries)
		assert first.status_code == 200
		assert set(first.json()['logo']) == {'medium'}

		with SessionLocal() as db:
			image_id = db.scalar(select(StoreImage.id).where(StoreImage.store_id == shop['store_id']))
			db.add(StoreImageVariant(store_image_id=image_id, variant='small', storage_path='stores/test/small.webp', mime_type='image/webp', width=256, height=128, size_bytes=100))
			db.commit()

		save_image(shop['store_id'], 'cover', {'medium': (960, 480), 'large': (1920, 960)})
		queries.clear()
		second = client.get('/stores/slug/saint')

		assert second.status_code == 200
		assert set(second.json()['logo']) == {'small', 'medium'}
		assert set(second.json()['cover']) == {'medium', 'large'}
		# A quantidade não cresce com as variantes; não fixa o total de queries do endpoint.
		assert len(queries) == first_count
	finally:
		event.remove(engine, 'before_cursor_execute', record_query)


def test_basic_read_and_update_keep_their_contract_when_store_has_images(client, shop):
	save_image(shop['store_id'], 'logo', {'medium': (512, 256)})
	expected = {'id': str(shop['store_id']), 'name': 'Saint', 'slug': 'saint', 'description': 'Streetwear.'}
	response = client.get(f"/stores/{shop['store_id']}")

	assert response.status_code == 200
	assert response.json() == expected

	updated = client.patch(f"/stores/{shop['store_id']}", json={'description': 'Nova descrição.'}, headers={'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"})

	assert updated.status_code == 200
	assert updated.json() == {**expected, 'description': 'Nova descrição.'}

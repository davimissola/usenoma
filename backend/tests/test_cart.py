from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier
from unittest.mock import Mock
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.main import app
from app.modules.auth.security import create_access_token
from app.modules.cart import service
from app.modules.cart.models import Cart, CartItem
from app.modules.cart.schemas import MAX_QUANTITY
from app.modules.products.models import Product, ProductImage, ProductSize
from app.modules.stores import storage as store_storage
from app.modules.stores.models import StoreImage, StoreImageVariant


def headers_for(user_id):
	return {'Authorization': f'Bearer {create_access_token(user_id)}'}


@pytest.fixture
def cart_logo_storage(monkeypatch):
	monkeypatch.setattr(settings, 'supabase_url', 'https://cart-project.supabase.co')
	monkeypatch.setattr(settings, 'supabase_storage_bucket', 'store-media')
	request = Mock(side_effect=AssertionError('Consultar logos não deve fazer chamadas ao Storage.'))
	for method in ['get', 'post', 'request']:
		monkeypatch.setattr(store_storage.httpx, method, request)
	yield
	request.assert_not_called()


def save_cart_store_image(store_id, image_type='logo', variants=('small', 'medium'), mime_type='image/webp'):
	with SessionLocal() as db:
		image = StoreImage(store_id=store_id, type=image_type)
		db.add(image)
		db.flush()
		for variant in variants:
			# Dimensões iguais também ocorrem quando o original é pequeno e não sofre upscale.
			db.add(StoreImageVariant(store_image_id=image.id, variant=variant, storage_path=f'stores/{store_id}/{image_type}/{variant}', mime_type=mime_type, width=128, height=128, size_bytes=500))
		db.commit()
		return image.id


@pytest.fixture
def catalog(shop, product):
	with SessionLocal() as db:
		other = Product(store_id=shop['other_store_id'], name='Outra camiseta', price=Decimal('0.30'))
		db.add(other)
		db.flush()
		db.add_all([ProductSize(product_id=product, size='M', available=True), ProductSize(product_id=product, size='G', available=True), ProductSize(product_id=product, size='P', available=False), ProductSize(product_id=other.id, size='M', available=True)])
		db.commit()
		return {'product_id': product, 'other_id': other.id}


def add(client, shop, product_id, size='M', quantity=1, user='new_user_id'):
	return client.post('/cart/items', json={'product_id': str(product_id), 'size': size, 'quantity': quantity}, headers=headers_for(shop[user]))


def test_get_empty_cart_does_not_create_or_modify_anything(client, shop):
	headers = headers_for(shop['new_user_id'])
	for _ in range(2):
		response = client.get('/cart', headers=headers)
		assert response.status_code == 200
		assert response.json() == {'id': None, 'updated_at': None, 'items': []}
		assert response.headers['Cache-Control'] == 'no-store'
	assert client.delete('/cart', headers=headers).status_code == 204
	with SessionLocal() as db:
		assert db.scalars(select(Cart)).all() == []


def test_first_add_creates_cart_with_live_prices_store_and_primary_image(client, shop, catalog, product_storage):
	with SessionLocal() as db:
		db.add_all([ProductImage(product_id=catalog['product_id'], position=2, storage_path='products/second/large.webp'), ProductImage(product_id=catalog['product_id'], position=1, storage_path='products/first/large.webp')])
		db.commit()

	response = add(client, shop, catalog['product_id'], size=' m ', quantity=2)
	assert response.status_code == 200
	data = response.json()
	assert data['id'] is not None
	assert datetime.fromisoformat(data['updated_at']).tzinfo is not None
	item = data['items'][0]
	assert item['product'] == {'id': str(catalog['product_id']), 'name': 'Camiseta', 'description': 'Algodão.', 'sizes': ['G', 'M']}
	assert item['size'] == 'M'
	assert item['quantity'] == 2
	assert item['unit_price'] == '149.90'
	assert item['subtotal'] == '299.80'
	assert item['store']['id'] == str(shop['store_id'])
	assert item['store']['slug'] == 'saint'
	assert item['store']['logo_url'] is None
	assert item['image']['position'] == 1
	assert item['image']['variants']['card']['url'].endswith('/first/card.webp')
	assert item['available'] is True
	assert item['unavailable_reason'] is None
	assert all(field not in response.text for field in ['storage_path', 'password_hash', 'email', 'user_id', 'role'])
	product_storage[0].assert_not_called()
	product_storage[1].assert_not_called()
	assert client.get('/cart', headers=headers_for(shop['new_user_id'])).json() == data


def test_same_product_and_size_increment_quantity_and_keep_item_id(client, shop, catalog):
	first = add(client, shop, catalog['product_id'], quantity=2).json()
	second = add(client, shop, catalog['product_id'], size='m', quantity=3).json()
	assert second['id'] == first['id']
	assert len(second['items']) == 1
	assert second['items'][0]['id'] == first['items'][0]['id']
	assert second['items'][0]['quantity'] == 5
	assert second['items'][0]['subtotal'] == '749.50'
	assert datetime.fromisoformat(second['updated_at']) > datetime.fromisoformat(first['updated_at'])


def test_different_sizes_and_stores_coexist_in_one_cart(client, shop, catalog):
	first = add(client, shop, catalog['product_id'], size='M').json()
	add(client, shop, catalog['product_id'], size='G')
	response = add(client, shop, catalog['other_id'], quantity=3)
	assert response.status_code == 200
	data = response.json()
	assert data['id'] == first['id']
	assert len(data['items']) == 3
	assert {(item['product_id'], item['size']) for item in data['items']} == {(str(catalog['product_id']), 'M'), (str(catalog['product_id']), 'G'), (str(catalog['other_id']), 'M')}
	assert {item['store']['id'] for item in data['items']} == {str(shop['store_id']), str(shop['other_store_id'])}
	assert next(item for item in data['items'] if item['product_id'] == str(catalog['other_id']))['subtotal'] == '0.90'
	assert all(item['image'] is None for item in data['items'])


def test_patch_replaces_quantity_and_changes_size_without_changing_item_id(client, shop, catalog):
	first = add(client, shop, catalog['product_id'], quantity=2).json()
	item_id = first['items'][0]['id']
	headers = headers_for(shop['new_user_id'])
	response = client.patch(f'/cart/items/{item_id}', json={'quantity': 3}, headers=headers)
	assert response.status_code == 200
	assert response.json()['items'][0]['quantity'] == 3
	response = client.patch(f'/cart/items/{item_id}', json={'size': 'g', 'quantity': 4}, headers=headers)
	assert response.status_code == 200
	assert response.json()['items'][0]['id'] == item_id
	assert response.json()['items'][0]['size'] == 'G'
	assert response.json()['items'][0]['quantity'] == 4
	assert response.json()['items'][0]['subtotal'] == '599.60'


@pytest.mark.parametrize('quantity, expected', [(None, 5), (4, 7)])
def test_size_change_merges_into_existing_item(client, shop, catalog, quantity, expected):
	first = add(client, shop, catalog['product_id'], size='M', quantity=2).json()
	source_id = first['items'][0]['id']
	second = add(client, shop, catalog['product_id'], size='G', quantity=3).json()
	target_id = next(item['id'] for item in second['items'] if item['size'] == 'G')
	data = {'size': 'G'}
	if quantity is not None:
		data['quantity'] = quantity
	response = client.patch(f'/cart/items/{source_id}', json=data, headers=headers_for(shop['new_user_id']))
	assert response.status_code == 200
	assert len(response.json()['items']) == 1
	assert response.json()['items'][0]['id'] == target_id
	assert response.json()['items'][0]['quantity'] == expected
	with SessionLocal() as db:
		assert db.get(CartItem, UUID(source_id)) is None


def test_remove_last_item_preserves_cart_and_clear_is_idempotent(client, shop, catalog):
	data = add(client, shop, catalog['product_id']).json()
	headers = headers_for(shop['new_user_id'])
	assert client.delete(f"/cart/items/{data['items'][0]['id']}", headers=headers).status_code == 204
	empty = client.get('/cart', headers=headers).json()
	assert empty['id'] == data['id']
	assert empty['items'] == []
	assert datetime.fromisoformat(empty['updated_at']) > datetime.fromisoformat(data['updated_at'])
	assert client.delete('/cart', headers=headers).status_code == 204
	assert client.get('/cart', headers=headers).json() == empty

	add(client, shop, catalog['product_id'])
	full = add(client, shop, catalog['other_id']).json()
	assert client.delete('/cart', headers=headers).status_code == 204
	cleared = client.get('/cart', headers=headers).json()
	assert cleared['id'] == data['id']
	assert cleared['items'] == []
	assert datetime.fromisoformat(cleared['updated_at']) > datetime.fromisoformat(full['updated_at'])
	assert client.delete('/cart', headers=headers).status_code == 204
	assert client.get('/cart', headers=headers).json() == cleared


@pytest.mark.parametrize('payload', [{}, {'size': 'm'}, {'quantity': 2}, {'size': 'M', 'quantity': 2}])
def test_get_and_noop_patch_do_not_change_updated_at(client, shop, catalog, payload):
	data = add(client, shop, catalog['product_id'], quantity=2).json()
	headers = headers_for(shop['new_user_id'])
	assert client.get('/cart', headers=headers).json() == data
	response = client.patch(f"/cart/items/{data['items'][0]['id']}", json=payload, headers=headers)
	assert response.status_code == 200
	assert response.json() == data
	assert client.get('/cart', headers=headers).json() == data


def test_catalog_price_change_is_reflected_without_cart_timestamp_change(client, shop, catalog):
	data = add(client, shop, catalog['product_id'], quantity=3).json()
	with SessionLocal() as db:
		db.get(Product, catalog['product_id']).price = Decimal('0.10')
		db.commit()
	response = client.get('/cart', headers=headers_for(shop['new_user_id'])).json()
	assert response['updated_at'] == data['updated_at']
	assert response['items'][0]['unit_price'] == '0.10'
	assert response['items'][0]['subtotal'] == '0.30'


@pytest.mark.parametrize('change, reason', [('disable', 'size_unavailable'), ('remove_size', 'size_removed'), ('remove_product', 'product_removed')])
def test_unavailable_items_are_preserved_and_can_be_removed(client, shop, catalog, change, reason):
	data = add(client, shop, catalog['product_id'], quantity=2).json()
	item_id = data['items'][0]['id']
	with SessionLocal() as db:
		if change == 'disable':
			db.get(ProductSize, (catalog['product_id'], 'M')).available = False
		elif change == 'remove_size':
			db.delete(db.get(ProductSize, (catalog['product_id'], 'M')))
		else:
			db.delete(db.get(Product, catalog['product_id']))
		db.commit()

	headers = headers_for(shop['new_user_id'])
	response = client.get('/cart', headers=headers)
	assert response.status_code == 200
	current = response.json()
	assert current['updated_at'] == data['updated_at']
	assert len(current['items']) == 1
	item = current['items'][0]
	assert item['id'] == item_id
	assert item['quantity'] == 2
	assert item['size'] == 'M'
	assert item['available'] is False
	assert item['unavailable_reason'] == reason
	if change == 'remove_product':
		assert item['product_id'] is None
		assert all(item[field] is None for field in ['product', 'unit_price', 'subtotal', 'store', 'image'])
	else:
		assert item['unit_price'] == '149.90'
	assert client.delete(f'/cart/items/{item_id}', headers=headers).status_code == 204


def test_reenabled_size_becomes_available_and_can_be_changed_to_another_size(client, shop, catalog):
	data = add(client, shop, catalog['product_id']).json()
	with SessionLocal() as db:
		db.get(ProductSize, (catalog['product_id'], 'M')).available = False
		db.commit()
	headers = headers_for(shop['new_user_id'])
	assert client.get('/cart', headers=headers).json()['items'][0]['available'] is False
	with SessionLocal() as db:
		db.get(ProductSize, (catalog['product_id'], 'M')).available = True
		db.commit()
	assert client.get('/cart', headers=headers).json()['items'][0]['available'] is True
	assert client.patch(f"/cart/items/{data['items'][0]['id']}", json={'size': 'G'}, headers=headers).status_code == 200


@pytest.mark.parametrize('change, status', [('disable', 409), ('remove_size', 404), ('remove_product', 404)])
def test_unavailable_item_cannot_be_increased_but_can_be_cleared(client, shop, catalog, change, status):
	data = add(client, shop, catalog['product_id']).json()
	with SessionLocal() as db:
		if change == 'disable':
			db.get(ProductSize, (catalog['product_id'], 'M')).available = False
		elif change == 'remove_size':
			db.delete(db.get(ProductSize, (catalog['product_id'], 'M')))
		else:
			db.delete(db.get(Product, catalog['product_id']))
		db.commit()
	headers = headers_for(shop['new_user_id'])
	before = client.get('/cart', headers=headers).json()
	assert add(client, shop, catalog['product_id']).status_code == status
	assert client.patch(f"/cart/items/{data['items'][0]['id']}", json={'quantity': 2}, headers=headers).status_code == status
	assert client.get('/cart', headers=headers).json() == before
	assert client.delete('/cart', headers=headers).status_code == 204
	assert client.get('/cart', headers=headers).json()['items'] == []


@pytest.mark.parametrize('size, status', [('X', 404), ('P', 409)])
def test_unknown_or_unavailable_size_does_not_create_cart(client, shop, catalog, size, status):
	assert add(client, shop, catalog['product_id'], size=size).status_code == status
	assert client.get('/cart', headers=headers_for(shop['new_user_id'])).json()['id'] is None


def test_product_and_size_must_belong_to_the_selected_product(client, shop, catalog):
	assert add(client, shop, uuid4()).status_code == 404
	assert add(client, shop, catalog['other_id'], size='G').status_code == 404
	assert client.get('/cart', headers=headers_for(shop['new_user_id'])).json()['id'] is None


@pytest.mark.parametrize('quantity', [0, -1, 1.5, True, '2', None, MAX_QUANTITY + 1])
def test_invalid_add_quantities_are_rejected_without_cart_creation(client, shop, catalog, quantity):
	assert add(client, shop, catalog['product_id'], quantity=quantity).status_code == 422
	assert client.get('/cart', headers=headers_for(shop['new_user_id'])).json()['id'] is None


@pytest.mark.parametrize('payload, status', [({'quantity': 0}, 422), ({'quantity': -1}, 422), ({'quantity': True}, 422), ({'quantity': '2'}, 422), ({'quantity': None}, 422), ({'size': None}, 422), ({'size': ''}, 422), ({'size': 'P'}, 409), ({'size': 'X'}, 404), ({'product_id': str(uuid4())}, 422), ({'cart_id': str(uuid4())}, 422)])
def test_invalid_patch_does_not_change_cart(client, shop, catalog, payload, status):
	data = add(client, shop, catalog['product_id']).json()
	headers = headers_for(shop['new_user_id'])
	response = client.patch(f"/cart/items/{data['items'][0]['id']}", json=payload, headers=headers)
	assert response.status_code == status
	assert client.get('/cart', headers=headers).json() == data


@pytest.mark.parametrize('method, path, payload', [('GET', '/cart', None), ('POST', '/cart/items', {'product_id': str(uuid4()), 'size': 'M', 'quantity': 1}), ('PATCH', '/cart/items/{item}', {'quantity': 2}), ('DELETE', '/cart/items/{item}', None), ('DELETE', '/cart', None)])
@pytest.mark.parametrize('token', [None, 'invalid', 'deleted_user', 'expired'])
def test_cart_routes_require_valid_existing_user(client, method, path, payload, token):
	headers = {}
	if token == 'deleted_user':
		headers = headers_for(uuid4())
	elif token == 'invalid':
		headers = {'Authorization': 'Bearer invalid'}
	elif token == 'expired':
		expired = jwt.encode({'sub': str(uuid4()), 'exp': datetime.now(timezone.utc) - timedelta(seconds=1)}, settings.secret_key.get_secret_value(), algorithm='HS256')
		headers = {'Authorization': f'Bearer {expired}'}
	response = client.request(method, path.format(item=uuid4()), json=payload, headers=headers)
	assert response.status_code == 401
	assert response.headers['WWW-Authenticate'] == 'Bearer'


def test_other_users_cannot_read_modify_or_clear_another_cart(client, shop, catalog):
	owner_cart = add(client, shop, catalog['product_id'], user='owner_id').json()
	user_cart = add(client, shop, catalog['other_id']).json()
	headers = headers_for(shop['new_user_id'])
	foreign_id = owner_cart['items'][0]['id']
	assert client.patch(f'/cart/items/{foreign_id}', json={'quantity': 9}, headers=headers).status_code == 404
	assert client.delete(f'/cart/items/{foreign_id}', headers=headers).status_code == 404
	assert client.get('/cart', headers=headers).json() == user_cart
	assert client.delete('/cart', headers=headers).status_code == 204
	assert client.get('/cart', headers=headers_for(shop['owner_id'])).json() == owner_cart


def test_missing_item_does_not_create_cart_or_touch_existing_cart(client, shop, catalog):
	headers = headers_for(shop['new_user_id'])
	assert client.patch(f'/cart/items/{uuid4()}', json={'quantity': 1}, headers=headers).status_code == 404
	assert client.delete(f'/cart/items/{uuid4()}', headers=headers).status_code == 404
	data = add(client, shop, catalog['product_id']).json()
	assert client.delete(f'/cart/items/{uuid4()}', headers=headers).status_code == 404
	assert client.get('/cart', headers=headers).json() == data


def test_quantity_overflow_does_not_change_existing_item(client, shop, catalog):
	data = add(client, shop, catalog['product_id'], quantity=MAX_QUANTITY).json()
	assert add(client, shop, catalog['product_id']).status_code == 422
	assert client.get('/cart', headers=headers_for(shop['new_user_id'])).json() == data


def test_quantity_overflow_during_size_merge_keeps_both_items(client, shop, catalog):
	add(client, shop, catalog['product_id'], size='M', quantity=MAX_QUANTITY)
	data = add(client, shop, catalog['product_id'], size='G').json()
	source_id = next(item['id'] for item in data['items'] if item['size'] == 'G')
	headers = headers_for(shop['new_user_id'])
	assert client.patch(f'/cart/items/{source_id}', json={'size': 'M'}, headers=headers).status_code == 422
	assert client.get('/cart', headers=headers).json() == data


@pytest.mark.parametrize('operation', ['add', 'quantity', 'size', 'remove', 'clear'])
def test_real_modifications_update_timestamp_in_utc(client, shop, catalog, operation):
	data = add(client, shop, catalog['product_id'], quantity=2).json()
	item_id = data['items'][0]['id']
	past = datetime(2000, 1, 1, tzinfo=timezone.utc)
	with SessionLocal() as db:
		db.get(Cart, UUID(data['id'])).updated_at = past
		db.commit()
	headers = headers_for(shop['new_user_id'])
	requests = {'add': ('POST', '/cart/items', {'product_id': str(catalog['product_id']), 'size': 'G', 'quantity': 1}), 'quantity': ('PATCH', f'/cart/items/{item_id}', {'quantity': 3}), 'size': ('PATCH', f'/cart/items/{item_id}', {'size': 'G'}), 'remove': ('DELETE', f'/cart/items/{item_id}', None), 'clear': ('DELETE', '/cart', None)}
	method, path, payload = requests[operation]
	before = datetime.now(timezone.utc)
	assert client.request(method, path, json=payload, headers=headers).status_code in {200, 204}
	current = client.get('/cart', headers=headers).json()
	updated = datetime.fromisoformat(current['updated_at'])
	assert before <= updated <= datetime.now(timezone.utc)
	assert updated > past


def test_product_delete_route_keeps_cart_item_as_unavailable(client, shop, catalog):
	data = add(client, shop, catalog['product_id']).json()
	response = client.delete(f"/stores/{shop['store_id']}/products/{catalog['product_id']}", headers=headers_for(shop['owner_id']))
	assert response.status_code == 204
	current = client.get('/cart', headers=headers_for(shop['new_user_id'])).json()
	assert current['items'][0]['id'] == data['items'][0]['id']
	assert current['items'][0]['unavailable_reason'] == 'product_removed'
	assert current['items'][0]['available'] is False
	assert current['updated_at'] == data['updated_at']


def test_removing_main_image_uses_next_image_without_marking_product_unavailable(client, shop, catalog, product_storage):
	with SessionLocal() as db:
		first = ProductImage(product_id=catalog['product_id'], position=1, storage_path='products/first/large.webp')
		second = ProductImage(product_id=catalog['product_id'], position=2, storage_path='products/second/large.webp')
		db.add_all([first, second])
		db.commit()
		first_id = first.id
	data = add(client, shop, catalog['product_id']).json()
	with SessionLocal() as db:
		db.delete(db.get(ProductImage, first_id))
		db.commit()
	current = client.get('/cart', headers=headers_for(shop['new_user_id'])).json()
	assert current['items'][0]['image']['variants']['card']['url'].endswith('/second/card.webp')
	assert current['items'][0]['available'] is True
	assert current['updated_at'] == data['updated_at']


@pytest.mark.parametrize('payload', [{'size': '   '}, {'size': 'ß' * 20}, {'quantity': 2, 'user_id': str(uuid4())}, {'quantity': 2, 'cart_id': str(uuid4())}])
def test_invalid_add_fields_do_not_create_cart(client, shop, catalog, payload):
	body = {'product_id': str(catalog['product_id']), 'size': 'M', 'quantity': 1, **payload}
	assert client.post('/cart/items', json=body, headers=headers_for(shop['new_user_id'])).status_code == 422
	assert client.get('/cart', headers=headers_for(shop['new_user_id'])).json()['id'] is None


def test_concurrent_first_adds_create_one_cart_and_accumulate_quantity(shop, catalog):
	barrier = Barrier(2)
	def add_once(quantity):
		with TestClient(app) as client:
			barrier.wait(timeout=10)
			return add(client, shop, catalog['product_id'], quantity=quantity).status_code
	with ThreadPoolExecutor(max_workers=2) as executor:
		assert list(executor.map(add_once, [2, 3])) == [200, 200]
	with SessionLocal() as db:
		assert len(db.scalars(select(Cart)).all()) == 1
		items = db.scalars(select(CartItem)).all()
		assert len(items) == 1
		assert items[0].quantity == 5


@pytest.mark.parametrize('operation', ['add', 'patch', 'remove', 'clear'])
def test_commit_failure_rolls_back_cart_items_and_timestamp(client, shop, catalog, monkeypatch, operation):
	data = add(client, shop, catalog['product_id']).json()
	item_id = data['items'][0]['id']
	headers = headers_for(shop['new_user_id'])
	monkeypatch.setattr(SessionLocal.class_, 'commit', Mock(side_effect=OperationalError('commit', {}, Exception('erro privado'))))
	requests = {'add': ('POST', '/cart/items', {'product_id': str(catalog['product_id']), 'size': 'G', 'quantity': 1}), 'patch': ('PATCH', f'/cart/items/{item_id}', {'quantity': 2}), 'remove': ('DELETE', f'/cart/items/{item_id}', None), 'clear': ('DELETE', '/cart', None)}
	method, path, payload = requests[operation]
	response = client.request(method, path, json=payload, headers=headers)
	assert response.status_code == 503
	assert 'erro privado' not in response.text
	assert client.get('/cart', headers=headers).json() == data


def test_response_failure_rolls_back_first_cart_creation(client, shop, catalog, product_storage, monkeypatch):
	monkeypatch.setattr(service, 'build_cart_response', Mock(side_effect=HTTPException(status_code=503, detail='Falha na resposta.')))
	assert add(client, shop, catalog['product_id']).status_code == 503
	with SessionLocal() as db:
		assert db.scalars(select(Cart)).all() == []
		assert db.scalars(select(CartItem)).all() == []


def test_cart_reads_do_not_add_queries_per_item(client, shop, catalog, product_storage):
	save_cart_store_image(shop['store_id'])
	save_cart_store_image(shop['other_store_id'])
	add(client, shop, catalog['product_id'])
	statements = []
	def count_queries(connection, cursor, statement, parameters, context, executemany):
		if statement.lstrip().upper().startswith('SELECT'):
			statements.append(statement)
	event.listen(engine, 'before_cursor_execute', count_queries)
	try:
		assert client.get('/cart', headers=headers_for(shop['new_user_id'])).status_code == 200
		initial_count = len(statements)
		add(client, shop, catalog['product_id'], size='G')
		add(client, shop, catalog['other_id'])
		statements.clear()
		response = client.get('/cart', headers=headers_for(shop['new_user_id']))
		assert response.status_code == 200
		assert len(response.json()['items']) == 3
		assert len(statements) == initial_count
		assert all(item['store']['logo_url'].endswith(f"/{item['store']['id']}/logo/small") for item in response.json()['items'])
	finally:
		event.remove(engine, 'before_cursor_execute', count_queries)


def test_cart_product_details_are_current_and_sizes_belong_to_each_product(client, shop, catalog):
	add(client, shop, catalog['product_id'])
	before = add(client, shop, catalog['other_id']).json()
	with SessionLocal() as db:
		db.get(Product, catalog['product_id']).description = 'Nova descrição.'
		db.get(ProductSize, (catalog['product_id'], 'M')).available = False
		db.delete(db.get(ProductSize, (catalog['product_id'], 'G')))
		db.add(ProductSize(product_id=catalog['product_id'], size='GG', available=True))
		db.commit()

	data = client.get('/cart', headers=headers_for(shop['new_user_id'])).json()
	assert data['updated_at'] == before['updated_at']
	items = {item['product_id']: item for item in data['items']}
	first = items[str(catalog['product_id'])]
	assert first['product']['description'] == 'Nova descrição.'
	assert first['product']['sizes'] == ['GG']
	assert first['size'] == 'M'
	assert first['unavailable_reason'] == 'size_unavailable'
	assert items[str(catalog['other_id'])]['product']['description'] is None
	assert items[str(catalog['other_id'])]['product']['sizes'] == ['M']


def test_cart_product_without_available_sizes_keeps_selected_size(client, shop, catalog):
	before = add(client, shop, catalog['product_id']).json()
	with SessionLocal() as db:
		for size in db.scalars(select(ProductSize).where(ProductSize.product_id == catalog['product_id'])):
			size.available = False
		db.commit()

	data = client.get('/cart', headers=headers_for(shop['new_user_id'])).json()
	assert data['updated_at'] == before['updated_at']
	assert data['items'][0]['product']['sizes'] == []
	assert data['items'][0]['size'] == 'M'
	assert data['items'][0]['unavailable_reason'] == 'size_unavailable'


@pytest.mark.parametrize('variants, expected, mime_type', [(['small', 'medium'], 'small', 'image/webp'), (['medium'], 'medium', 'image/png'), (['large'], 'large', 'image/jpeg'), ([], None, 'image/webp')])
def test_cart_returns_logo_url_using_available_variant(client, shop, catalog, cart_logo_storage, variants, expected, mime_type):
	save_cart_store_image(shop['store_id'], variants=variants, mime_type=mime_type)
	created = add(client, shop, catalog['product_id'])
	assert created.status_code == 200
	response = client.get('/cart', headers=headers_for(shop['new_user_id']))
	assert response.status_code == 200
	logo = response.json()['items'][0]['store']['logo_url']
	assert response.json() == created.json()
	if expected is None:
		assert logo is None
	else:
		assert logo == f"https://cart-project.supabase.co/storage/v1/object/public/store-media/stores/{shop['store_id']}/logo/{expected}"
	assert all(field not in response.text for field in ['storage_path', 'password_hash', 'user_id', 'members', 'role'])


def test_cart_never_uses_cover_or_another_store_logo(client, shop, catalog, cart_logo_storage):
	save_cart_store_image(shop['store_id'])
	save_cart_store_image(shop['other_store_id'], image_type='cover')
	add(client, shop, catalog['product_id'])
	response = add(client, shop, catalog['other_id'])
	assert response.status_code == 200
	items = {item['store']['id']: item for item in response.json()['items']}
	assert items[str(shop['store_id'])]['store']['logo_url'].endswith(f"/{shop['store_id']}/logo/small")
	assert items[str(shop['other_store_id'])]['store']['logo_url'] is None
	assert '/cover/' not in response.text


def test_cart_reflects_logo_replacement_and_removal_without_modifying_cart(client, shop, catalog, cart_logo_storage):
	image_id = save_cart_store_image(shop['store_id'])
	before = add(client, shop, catalog['product_id']).json()
	with SessionLocal() as db:
		db.get(StoreImageVariant, (image_id, 'small')).storage_path = 'stores/new-logo/small.webp'
		db.commit()
	updated = client.get('/cart', headers=headers_for(shop['new_user_id'])).json()
	assert updated['items'][0]['store']['logo_url'].endswith('/new-logo/small.webp')
	assert updated['updated_at'] == before['updated_at']
	with SessionLocal() as db:
		db.delete(db.get(StoreImage, image_id))
		db.commit()
	removed = client.get('/cart', headers=headers_for(shop['new_user_id'])).json()
	assert removed['items'][0]['store']['logo_url'] is None
	assert removed['updated_at'] == before['updated_at']


def test_cart_without_logos_does_not_require_storage_configuration(client, shop, catalog, monkeypatch):
	monkeypatch.setattr(settings, 'supabase_url', None)
	response = add(client, shop, catalog['product_id'])
	assert response.status_code == 200
	assert response.json()['items'][0]['store']['logo_url'] is None

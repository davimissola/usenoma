from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.auth.security import create_access_token
from app.modules.products.models import Product, ProductSize
from app.modules.stores.models import StoreMember


def headers_for(user_id):
	return {'Authorization': f'Bearer {create_access_token(user_id)}'}


@pytest.mark.parametrize('user', ['owner_id', 'manager_id'])
def test_members_can_create_update_and_delete_products(client, shop, user):
	base = f"/stores/{shop['store_id']}/products"
	headers = headers_for(shop[user])
	response = client.post(base, json={'name': ' Camiseta ', 'price': '0.30', 'description': 'Descrição.'}, headers=headers)
	assert response.status_code == 201
	data = response.json()
	assert data['name'] == 'Camiseta'
	assert data['price'] == '0.30'
	assert data['store_id'] == str(shop['store_id'])
	assert data['sizes'] == []
	assert data['images'] == []

	response = client.patch(f"{base}/{data['id']}", json={'price': '199.99', 'description': None}, headers=headers)
	assert response.status_code == 200
	assert response.json()['name'] == 'Camiseta'
	assert response.json()['price'] == '199.99'
	assert response.json()['description'] is None

	assert client.delete(f"{base}/{data['id']}", headers=headers).status_code == 204
	assert client.get(f"/products/{data['id']}").status_code == 404


@pytest.mark.parametrize('method, suffix, data', [('POST', '', {'name': 'Camiseta', 'price': '10.00'}), ('PATCH', '/{product}', {'name': 'Outra camiseta'}), ('DELETE', '/{product}', None), ('POST', '/{product}/sizes', {'size': 'M'}), ('PATCH', '/{product}/sizes/M', {'available': False}), ('DELETE', '/{product}/sizes/M', None)])
@pytest.mark.parametrize('user, status', [(None, 401), ('outsider_id', 403)])
def test_product_writes_require_membership(client, shop, product, method, suffix, data, user, status):
	headers = {}

	if user:
		headers = headers_for(shop[user])

	response = client.request(method, f"/stores/{shop['store_id']}/products{suffix.format(product=product)}", json=data, headers=headers)
	assert response.status_code == status


@pytest.mark.parametrize('method, suffix, data', [('PATCH', '', {'name': 'Outra camiseta'}), ('DELETE', '', None), ('POST', '/sizes', {'size': 'M'}), ('PATCH', '/sizes/M', {'available': False}), ('DELETE', '/sizes/M', None)])
def test_product_cannot_be_modified_through_another_store(client, shop, product, method, suffix, data):
	response = client.request(method, f"/stores/{shop['other_store_id']}/products/{product}{suffix}", json=data, headers=headers_for(shop['owner_id']))
	assert response.status_code == 404
	assert client.get(f'/products/{product}').json()['name'] == 'Camiseta'


@pytest.mark.parametrize('data', [{'price': '-0.01'}, {'price': 'NaN'}, {'price': 'Infinity'}, {'price': '1.001'}, {'price': '100000000.00'}, {'price': None}, {'name': ''}, {'name': None}, {'store_id': str(uuid4())}])
def test_invalid_product_update_is_rejected_without_changes(client, shop, product, data):
	response = client.patch(f"/stores/{shop['store_id']}/products/{product}", json=data, headers=headers_for(shop['owner_id']))
	assert response.status_code == 422
	stored = client.get(f'/products/{product}').json()
	assert stored['price'] == '149.90'
	assert stored['name'] == 'Camiseta'
	assert stored['store_id'] == str(shop['store_id'])


@pytest.mark.parametrize('user', ['owner_id', 'manager_id'])
def test_size_availability_and_explicit_removal(client, shop, product, user):
	base = f"/stores/{shop['store_id']}/products/{product}/sizes"
	headers = headers_for(shop[user])
	response = client.post(base, json={'size': ' m '}, headers=headers)
	assert response.status_code == 201
	assert response.json() == {'size': 'M', 'available': True}
	assert client.post(base, json={'size': 'm', 'available': False}, headers=headers).status_code == 409
	assert client.patch(f'{base}/M', json={'available': False}, headers=headers).json() == {'size': 'M', 'available': False}

	with SessionLocal() as db:
		assert db.get(ProductSize, (product, 'M')).available is False

	assert client.patch(f'{base}/M', json={'available': True}, headers=headers).status_code == 200
	assert client.delete(f'{base}/M', headers=headers).status_code == 204
	assert client.patch(f'{base}/M', json={'available': False}, headers=headers).status_code == 404


def test_size_ranges_with_slashes_can_be_updated_and_removed(client, shop, product):
	base = f"/stores/{shop['store_id']}/products/{product}/sizes"
	headers = headers_for(shop['owner_id'])
	assert client.post(base, json={'size': '40/42'}, headers=headers).status_code == 201
	assert client.patch(f'{base}/40%2F42', json={'available': False}, headers=headers).status_code == 200
	assert client.delete(f'{base}/40%2F42', headers=headers).status_code == 204


def test_size_length_is_checked_after_unicode_normalization(client, shop, product):
	response = client.post(f"/stores/{shop['store_id']}/products/{product}/sizes", json={'size': 'ß' * 20}, headers=headers_for(shop['owner_id']))
	assert response.status_code == 422

	with SessionLocal() as db:
		assert db.scalars(select(ProductSize)).all() == []


@pytest.mark.parametrize('data', [{'available': None}, {'available': 'false'}, {'available': 0}, {'size': 'G', 'available': False}])
def test_size_update_accepts_only_a_boolean_availability(client, shop, product, data):
	base = f"/stores/{shop['store_id']}/products/{product}/sizes"
	headers = headers_for(shop['owner_id'])
	client.post(base, json={'size': 'M'}, headers=headers)
	assert client.patch(f'{base}/M', json=data, headers=headers).status_code == 422

	with SessionLocal() as db:
		assert db.get(ProductSize, (product, 'M')).available is True


def test_missing_store_and_product_return_not_found(client, shop, product):
	headers = headers_for(shop['owner_id'])
	assert client.post(f'/stores/{uuid4()}/products', json={'name': 'Camiseta', 'price': '10.00'}, headers=headers).status_code == 404
	assert client.patch(f"/stores/{shop['store_id']}/products/{uuid4()}", json={'name': 'Camiseta'}, headers=headers).status_code == 404
	assert client.get(f'/products/{uuid4()}').status_code == 404
	assert client.get(f'/stores/{uuid4()}/products').status_code == 404


def test_create_does_not_accept_a_store_id_from_the_body(client, shop):
	response = client.post(f"/stores/{shop['store_id']}/products", json={'name': 'Camiseta', 'price': '10.00', 'store_id': str(shop['other_store_id'])}, headers=headers_for(shop['owner_id']))
	assert response.status_code == 422

	with SessionLocal() as db:
		assert db.scalars(select(Product)).all() == []


@pytest.mark.parametrize('data', [{'name': '   ', 'price': '10.00'}, {'name': 'x' * 121, 'price': '10.00'}, {'name': 'Camiseta', 'price': '-1.00'}, {'name': 'Camiseta', 'price': '0.001'}, {'name': 'Camiseta', 'price': 'NaN'}, {'name': 'Camiseta', 'price': True}, {'name': 'Camiseta'}, {'price': '10.00'}])
def test_invalid_creation_does_not_save_a_product(client, shop, data):
	response = client.post(f"/stores/{shop['store_id']}/products", json=data, headers=headers_for(shop['owner_id']))
	assert response.status_code == 422

	with SessionLocal() as db:
		assert db.scalars(select(Product)).all() == []


@pytest.mark.parametrize('data', [{'size': ''}, {'size': '   '}, {'size': 'x' * 21}, {'size': None}, {'size': 'M', 'available': 'false'}, {'size': 'M', 'available': None}, {'size': 'M', 'available': 0}])
def test_invalid_size_creation_preserves_existing_sizes(client, shop, product, data):
	response = client.post(f"/stores/{shop['store_id']}/products/{product}/sizes", json=data, headers=headers_for(shop['manager_id']))
	assert response.status_code == 422

	with SessionLocal() as db:
		assert db.scalars(select(ProductSize)).all() == []


def test_size_paths_are_normalized_and_unavailable_sizes_remain_stored(client, shop, product):
	base = f"/stores/{shop['store_id']}/products/{product}/sizes"
	headers = headers_for(shop['manager_id'])
	assert client.post(base, json={'size': ' m ', 'available': False}, headers=headers).status_code == 201
	assert client.get(f'/products/{product}').json()['sizes'] == []
	assert client.patch(f'{base}/m', json={'available': True}, headers=headers).status_code == 200
	assert client.get(f'/products/{product}').json()['sizes'] == [{'size': 'M', 'available': True}]
	assert client.delete(f'{base}/m', headers=headers).status_code == 204
	assert client.delete(f'{base}/m', headers=headers).status_code == 404


def test_removed_member_cannot_modify_products(client, shop, product):
	headers = headers_for(shop['manager_id'])
	with SessionLocal() as db:
		db.delete(db.get(StoreMember, (shop['store_id'], shop['manager_id'])))
		db.commit()

	assert client.patch(f"/stores/{shop['store_id']}/products/{product}", json={'name': 'Alterado'}, headers=headers).status_code == 403
	assert client.get(f'/products/{product}').json()['name'] == 'Camiseta'

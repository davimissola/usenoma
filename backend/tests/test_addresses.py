from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core.database import SessionLocal
from app.main import app
from app.modules.addresses.models import UserAddress
from app.modules.auth.security import create_access_token


URL = '/users/me/addresses'


def headers_for(user_id):
	return {'Authorization': f'Bearer {create_access_token(user_id)}'}


def create(client, shop, address_data, user='new_user_id', **changes):
	return client.post(URL, json={**address_data, **changes}, headers=headers_for(shop[user]))


def test_empty_list_does_not_create_an_address(client, shop):
	response = client.get(URL, headers=headers_for(shop['new_user_id']))
	assert response.status_code == 200
	assert response.json() == []
	assert response.headers['Cache-Control'] == 'no-store'
	with SessionLocal() as db:
		assert db.scalars(select(UserAddress)).all() == []


@pytest.mark.parametrize('is_default', [False, True])
def test_first_address_is_default_even_when_false_is_sent(client, shop, address_data, is_default):
	response = create(client, shop, address_data, is_default=is_default)
	assert response.status_code == 201
	data = response.json()
	assert data == {**address_data, 'id': data['id'], 'complement': None, 'is_default': True}
	assert 'user_id' not in data
	assert response.headers['Cache-Control'] == 'no-store'
	with SessionLocal() as db:
		assert db.get(UserAddress, UUID(data['id'])).user_id == shop['new_user_id']


def test_complete_crud_preserves_omitted_fields_and_can_clear_complement(client, shop, address_data):
	data = create(client, shop, address_data).json()
	path = f"{URL}/{data['id']}"
	headers = headers_for(shop['new_user_id'])
	response = client.get(path, headers=headers)
	assert response.status_code == 200
	assert response.json() == data
	assert response.headers['Cache-Control'] == 'no-store'

	changes = {'recipient_name': ' João Santos ', 'postal_code': '20040-020', 'street': ' Rua da Assembleia ', 'number': 'S/N', 'complement': ' Sala 2 ', 'neighborhood': 'Centro', 'city': 'Rio de Janeiro', 'state': ' rj ', 'phone': '+55 (21) 99999-4444'}
	response = client.patch(path, json=changes, headers=headers)
	assert response.status_code == 200
	updated = response.json()
	assert updated == {'id': data['id'], 'recipient_name': 'João Santos', 'postal_code': '20040020', 'street': 'Rua da Assembleia', 'number': 'S/N', 'complement': 'Sala 2', 'neighborhood': 'Centro', 'city': 'Rio de Janeiro', 'state': 'RJ', 'phone': '21999994444', 'is_default': True}
	assert client.get(path, headers=headers).json() == updated
	assert client.patch(path, json={}, headers=headers).json() == updated
	assert response.headers['Cache-Control'] == 'no-store'
	response = client.patch(path, json={'complement': None}, headers=headers)
	assert response.json() == {**updated, 'complement': None}
	assert client.delete(path, headers=headers).status_code == 204
	assert client.get(path, headers=headers).status_code == 404
	assert client.get(URL, headers=headers).json() == []


def test_second_address_keeps_first_default_and_list_is_paginated(client, shop, address_data):
	first = create(client, shop, address_data).json()
	second = create(client, shop, address_data, number='20').json()
	third = create(client, shop, address_data, number='30').json()
	assert second['is_default'] is False
	assert third['is_default'] is False
	headers = headers_for(shop['new_user_id'])
	response = client.get(URL, headers=headers)
	assert response.status_code == 200
	expected_ids = [first['id'], *sorted([second['id'], third['id']])]
	assert [item['id'] for item in response.json()] == expected_ids
	assert [item['id'] for item in client.get(URL, params={'offset': 1, 'limit': 1}, headers=headers).json()] == expected_ids[1:2]
	assert client.get(URL, params={'offset': 10}, headers=headers).json() == []


@pytest.mark.parametrize('method', ['POST', 'PATCH'])
def test_setting_default_only_changes_the_current_users_addresses(client, shop, address_data, method):
	first = create(client, shop, address_data).json()
	second = create(client, shop, address_data, number='20').json()
	other = create(client, shop, address_data, user='outsider_id').json()
	headers = headers_for(shop['new_user_id'])
	if method == 'POST':
		response = create(client, shop, address_data, is_default=True)
		assert response.status_code == 201
	else:
		response = client.patch(f"{URL}/{second['id']}", json={'is_default': True}, headers=headers)
		assert response.status_code == 200
	current = response.json()
	assert current['is_default'] is True
	assert client.get(f"{URL}/{first['id']}", headers=headers).json()['is_default'] is False
	assert client.patch(f"{URL}/{current['id']}", json={'is_default': True}, headers=headers).json() == current
	assert sum(item['is_default'] for item in client.get(URL, headers=headers).json()) == 1
	assert client.get(URL, headers=headers_for(shop['outsider_id'])).json() == [other]


def test_current_default_cannot_be_unset_and_rejected_patch_changes_nothing(client, shop, address_data):
	first = create(client, shop, address_data).json()
	second = create(client, shop, address_data, number='20').json()
	headers = headers_for(shop['new_user_id'])
	response = client.patch(f"{URL}/{first['id']}", json={'is_default': False, 'street': 'Outra rua'}, headers=headers)
	assert response.status_code == 409
	assert client.get(f"{URL}/{first['id']}", headers=headers).json() == first
	assert client.patch(f"{URL}/{second['id']}", json={'is_default': False}, headers=headers).json() == second


def test_deleting_default_promotes_another_address_without_affecting_other_users(client, shop, address_data):
	first = create(client, shop, address_data).json()
	second = create(client, shop, address_data, number='20').json()
	third = create(client, shop, address_data, number='30').json()
	other = create(client, shop, address_data, user='outsider_id').json()
	headers = headers_for(shop['new_user_id'])
	assert client.delete(f"{URL}/{first['id']}", headers=headers).status_code == 204
	remaining = client.get(URL, headers=headers).json()
	assert len(remaining) == 2
	assert sum(item['is_default'] for item in remaining) == 1
	assert remaining[0]['id'] == min(second['id'], third['id'])
	assert remaining[0]['is_default'] is True
	assert client.get(URL, headers=headers_for(shop['outsider_id'])).json() == [other]


def test_deleting_non_default_does_not_change_default(client, shop, address_data):
	first = create(client, shop, address_data).json()
	second = create(client, shop, address_data).json()
	headers = headers_for(shop['new_user_id'])
	assert client.delete(f"{URL}/{second['id']}", headers=headers).status_code == 204
	assert client.get(URL, headers=headers).json() == [first]


def test_deleting_last_address_allows_a_new_first_default(client, shop, address_data):
	first = create(client, shop, address_data).json()
	headers = headers_for(shop['new_user_id'])
	assert client.delete(f"{URL}/{first['id']}", headers=headers).status_code == 204
	assert client.get(URL, headers=headers).json() == []
	assert create(client, shop, address_data).json()['is_default'] is True


@pytest.mark.parametrize('complement', [None, '', ' \t '])
def test_empty_complement_is_stored_as_null(client, shop, address_data, complement):
	response = create(client, shop, address_data, complement=complement)
	assert response.status_code == 201
	data = response.json()
	assert data['complement'] is None
	headers = headers_for(shop['new_user_id'])
	client.patch(f"{URL}/{data['id']}", json={'complement': 'Apto 3'}, headers=headers)
	response = client.patch(f"{URL}/{data['id']}", json={'complement': complement}, headers=headers)
	assert response.status_code == 200
	assert response.json()['complement'] is None


@pytest.mark.parametrize('phone, expected', [('(11) 3333-4444', '1133334444'), ('+55 (11) 99999-8888', '11999998888'), ('5511999998888', '11999998888'), ('55999998888', '55999998888')])
def test_brazilian_phone_formats_preserve_ddd_and_leading_digits(client, shop, address_data, phone, expected):
	response = create(client, shop, address_data, phone=phone)
	assert response.status_code == 201
	assert response.json()['phone'] == expected


@pytest.mark.parametrize('method', ['GET', 'PATCH', 'DELETE'])
def test_another_users_address_is_not_visible_or_modifiable(client, shop, address_data, method):
	data = create(client, shop, address_data).json()
	kwargs = {}
	if method == 'PATCH':
		kwargs['json'] = {'is_default': True, 'recipient_name': 'Outro nome'}
	response = client.request(method, f"{URL}/{data['id']}", headers=headers_for(shop['outsider_id']), **kwargs)
	assert response.status_code == 404
	assert response.json() == {'detail': 'Endereço não encontrado.'}
	assert client.get(URL, headers=headers_for(shop['outsider_id'])).json() == []
	assert client.get(URL, headers=headers_for(shop['new_user_id'])).json() == [data]


@pytest.mark.parametrize('method', ['GET', 'PATCH', 'DELETE'])
def test_unknown_address_returns_404_and_invalid_id_returns_422(client, shop, method):
	kwargs = {}
	if method == 'PATCH':
		kwargs['json'] = {'number': '22'}
	headers = headers_for(shop['new_user_id'])
	assert client.request(method, f'{URL}/{uuid4()}', headers=headers, **kwargs).status_code == 404
	assert client.request(method, f'{URL}/invalido', headers=headers, **kwargs).status_code == 422


@pytest.mark.parametrize('method, path', [('GET', URL), ('POST', URL), ('GET', f'{URL}/{uuid4()}'), ('PATCH', f'{URL}/{uuid4()}'), ('DELETE', f'{URL}/{uuid4()}')])
def test_all_address_routes_require_authentication(client, address_data, method, path):
	response = client.request(method, path, json=address_data)
	assert response.status_code == 401


@pytest.mark.parametrize('method', ['POST', 'PATCH', 'DELETE'])
def test_writes_reject_a_jwt_whose_user_no_longer_exists(client, address_data, method):
	path = URL
	if method != 'POST':
		path = f'{URL}/{uuid4()}'
	assert client.request(method, path, json=address_data, headers=headers_for(uuid4())).status_code == 401


@pytest.mark.parametrize('method', ['POST', 'PATCH'])
@pytest.mark.parametrize('changes', [
	{'recipient_name': '   '}, {'recipient_name': 'x' * 121}, {'postal_code': '1234'}, {'postal_code': '0100-1000'}, {'postal_code': 1001000},
	{'street': '\t'}, {'street': 'x' * 201}, {'number': 10}, {'number': ''}, {'number': 'x' * 21}, {'neighborhood': ' '}, {'city': ''},
	{'state': 'XX'}, {'state': 'São Paulo'}, {'phone': '12345'}, {'phone': '+1 (212) 555-1234'}, {'phone': 11999998888}, {'phone': '11999998888abc'},
	{'complement': 'x' * 121}, {'complement': 10}, {'is_default': 'false'}, {'is_default': 1}, {'user_id': str(uuid4())}, {'country': 'US'},
])
def test_invalid_fields_are_rejected_without_changing_addresses(client, shop, address_data, method, changes):
	first = create(client, shop, address_data).json()
	headers = headers_for(shop['new_user_id'])
	path = URL
	payload = {**address_data, **changes}
	if method == 'PATCH':
		path = f"{URL}/{first['id']}"
		payload = changes
	response = client.request(method, path, json=payload, headers=headers)
	assert response.status_code == 422
	assert all('input' not in error and 'ctx' not in error for error in response.json()['detail'])
	assert client.get(URL, headers=headers).json() == [first]


@pytest.mark.parametrize('field', ['recipient_name', 'postal_code', 'street', 'number', 'neighborhood', 'city', 'state', 'phone', 'is_default'])
def test_patch_rejects_explicit_null_for_required_fields(client, shop, address_data, field):
	first = create(client, shop, address_data).json()
	headers = headers_for(shop['new_user_id'])
	assert client.patch(f"{URL}/{first['id']}", json={field: None}, headers=headers).status_code == 422
	assert client.get(URL, headers=headers).json() == [first]


@pytest.mark.parametrize('query', [{'offset': -1}, {'limit': 0}, {'limit': 101}])
def test_pagination_rejects_invalid_limits(client, shop, query):
	assert client.get(URL, params=query, headers=headers_for(shop['new_user_id'])).status_code == 422


@pytest.mark.parametrize('operation', ['create', 'patch', 'delete'])
def test_commit_failure_rolls_back_the_whole_default_change(client, shop, address_data, monkeypatch, operation):
	first = create(client, shop, address_data).json()
	second = create(client, shop, address_data).json()
	headers = headers_for(shop['new_user_id'])
	before = client.get(URL, headers=headers).json()
	monkeypatch.setattr(SessionLocal.class_, 'commit', Mock(side_effect=OperationalError('commit', {}, Exception('dado privado'))))
	if operation == 'create':
		response = create(client, shop, address_data, is_default=True)
	elif operation == 'patch':
		response = client.patch(f"{URL}/{second['id']}", json={'is_default': True}, headers=headers)
	else:
		response = client.delete(f"{URL}/{first['id']}", headers=headers)
	assert response.status_code == 503
	assert 'dado privado' not in response.text
	assert client.get(URL, headers=headers).json() == before


@pytest.mark.parametrize('scenario', ['first_addresses', 'change_default', 'create_and_change', 'delete_and_change', 'delete_last_two'])
def test_concurrent_writes_keep_one_default_or_no_addresses(client, shop, address_data, scenario):
	headers = headers_for(shop['new_user_id'])
	if scenario == 'first_addresses':
		operations = [('POST', URL, address_data, 201), ('POST', URL, {**address_data, 'number': '20'}, 201)]
	else:
		first = create(client, shop, address_data).json()
		second = create(client, shop, address_data).json()
		if scenario == 'change_default':
			third = create(client, shop, address_data).json()
			operations = [('PATCH', f"{URL}/{second['id']}", {'is_default': True}, 200), ('PATCH', f"{URL}/{third['id']}", {'is_default': True}, 200)]
		elif scenario == 'create_and_change':
			operations = [('POST', URL, {**address_data, 'is_default': True}, 201), ('PATCH', f"{URL}/{second['id']}", {'is_default': True}, 200)]
		elif scenario == 'delete_and_change':
			operations = [('DELETE', f"{URL}/{first['id']}", None, 204), ('PATCH', f"{URL}/{second['id']}", {'is_default': True}, 200)]
		else:
			operations = [('DELETE', f"{URL}/{first['id']}", None, 204), ('DELETE', f"{URL}/{second['id']}", None, 204)]

	barrier = Barrier(2)
	def execute(operation):
		method, path, payload, expected_status = operation
		with TestClient(app) as concurrent_client:
			barrier.wait(timeout=10)
			response = concurrent_client.request(method, path, json=payload, headers=headers)
			assert response.status_code == expected_status, response.text

	with ThreadPoolExecutor(max_workers=2) as executor:
		list(executor.map(execute, operations))

	addresses = client.get(URL, headers=headers).json()
	if scenario == 'delete_last_two':
		assert addresses == []
	else:
		assert sum(item['is_default'] for item in addresses) == 1
		if scenario == 'first_addresses':
			assert len(addresses) == 2
		if scenario == 'delete_and_change':
			assert addresses[0]['id'] == second['id']

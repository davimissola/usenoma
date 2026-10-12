from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.main import app
from app.modules.auth.security import create_access_token
from app.modules.stores.models import Store, StoreMember
from app.modules.users.models import User


def headers_for(user_id):
	return {'Authorization': f'Bearer {create_access_token(user_id)}'}


@pytest.mark.parametrize('lookup', ['id', 'slug'])
def test_store_basic_data_is_public_and_contains_only_public_fields(client, shop, lookup):
	if lookup == 'id':
		path = f"/stores/{shop['store_id']}"
	else:
		path = '/stores/slug/saint'

	response = client.get(path)

	assert response.status_code == 200
	assert response.json() == {'id': str(shop['store_id']), 'name': 'Saint', 'slug': 'saint', 'description': 'Streetwear.'}


def test_unknown_store_and_invalid_id_return_coherent_errors(client):
	assert client.get(f'/stores/{uuid4()}').status_code == 404
	assert client.get('/stores/slug/inexistente').status_code == 404
	assert client.get('/stores/id-invalido').status_code == 422


def test_store_creation_is_not_exposed_as_a_public_endpoint(client, shop):
	response = client.post('/stores', json={'name': 'Outra loja', 'slug': 'outra-loja'}, headers=headers_for(shop['owner_id']))

	assert response.status_code == 404

	with SessionLocal() as db:
		assert db.scalar(select(func.count()).select_from(Store)) == 2


@pytest.mark.parametrize('user', ['owner_id', 'manager_id'])
def test_owner_and_manager_can_edit_basic_data(client, shop, user):
	response = client.patch(f"/stores/{shop['store_id']}", json={'name': ' Saint nova ', 'slug': 'saint-nova', 'description': 'Nova descrição.'}, headers=headers_for(shop[user]))

	assert response.status_code == 200
	assert response.json() == {'id': str(shop['store_id']), 'name': 'Saint nova', 'slug': 'saint-nova', 'description': 'Nova descrição.'}
	assert client.get('/stores/slug/saint').status_code == 404
	assert client.get('/stores/slug/saint-nova').status_code == 200


def test_partial_update_preserves_omitted_fields_and_can_clear_description(client, shop):
	response = client.patch(f"/stores/{shop['store_id']}", json={'description': None}, headers=headers_for(shop['owner_id']))

	assert response.status_code == 200
	assert response.json() == {'id': str(shop['store_id']), 'name': 'Saint', 'slug': 'saint', 'description': None}


@pytest.mark.parametrize('data', [{'name': None}, {'slug': None}, {'name': '   '}, {'name': 'x' * 121}, {'slug': 'Saint'}, {'slug': 'loja teste'}, {'slug': ''}, {'id': str(uuid4())}])
def test_invalid_basic_data_does_not_change_store(client, shop, data):
	response = client.patch(f"/stores/{shop['store_id']}", json=data, headers=headers_for(shop['owner_id']))

	assert response.status_code == 422
	assert client.get(f"/stores/{shop['store_id']}").json()['name'] == 'Saint'


def test_duplicate_slug_returns_conflict_and_rolls_back_other_changes(client, shop):
	response = client.patch(f"/stores/{shop['store_id']}", json={'name': 'Nome que não deve ser salvo', 'slug': 'noma-brasil'}, headers=headers_for(shop['owner_id']))

	assert response.status_code == 409
	assert response.json() == {'detail': 'Slug já utilizado por outra loja.'}
	assert client.get(f"/stores/{shop['store_id']}").json()['name'] == 'Saint'


@pytest.mark.parametrize('method, suffix, data', [('PATCH', '', {'name': 'Outro nome'}), ('GET', '/members', None), ('POST', '/members', {'role': 'manager'}), ('PATCH', '/members/{target}', {'role': 'owner'}), ('DELETE', '/members/{target}', None)])
def test_protected_store_operations_require_bearer_token(client, shop, method, suffix, data):
	suffix = suffix.format(target=shop['manager_id'])

	if method == 'POST':
		data = {**data, 'user_id': str(shop['new_user_id'])}

	response = client.request(method, f"/stores/{shop['store_id']}{suffix}", json=data)

	assert response.status_code == 401


@pytest.mark.parametrize('method, suffix, data', [('PATCH', '', {'name': 'Outro nome'}), ('GET', '/members', None), ('POST', '/members', {'role': 'manager'}), ('PATCH', '/members/{target}', {'role': 'owner'}), ('DELETE', '/members/{target}', None)])
def test_owner_of_another_store_cannot_administer_this_store(client, shop, method, suffix, data):
	suffix = suffix.format(target=shop['manager_id'])

	if method == 'POST':
		data = {**data, 'user_id': str(shop['new_user_id'])}

	response = client.request(method, f"/stores/{shop['store_id']}{suffix}", json=data, headers=headers_for(shop['outsider_id']))

	assert response.status_code == 403

	with SessionLocal() as db:
		assert db.get(Store, shop['store_id']).name == 'Saint'
		assert db.get(StoreMember, (shop['store_id'], shop['manager_id'])).role == 'manager'
		assert db.get(StoreMember, (shop['store_id'], shop['new_user_id'])) is None


@pytest.mark.parametrize('method, suffix, data', [('GET', '', None), ('POST', '', {'role': 'owner'}), ('PATCH', '/{target}', {'role': 'owner'}), ('DELETE', '/{target}', None)])
def test_manager_cannot_list_or_manage_members(client, shop, method, suffix, data):
	suffix = suffix.format(target=shop['owner_id'])

	if method == 'POST':
		data = {**data, 'user_id': str(shop['new_user_id'])}

	response = client.request(method, f"/stores/{shop['store_id']}/members{suffix}", json=data, headers=headers_for(shop['manager_id']))

	assert response.status_code == 403

	with SessionLocal() as db:
		assert db.get(StoreMember, (shop['store_id'], shop['owner_id'])).role == 'owner'
		assert db.get(StoreMember, (shop['store_id'], shop['new_user_id'])) is None


def test_same_user_can_have_different_permissions_in_different_stores(client, shop):
	headers = headers_for(shop['owner_id'])
	edit = client.patch(f"/stores/{shop['other_store_id']}", json={'description': 'Permitido ao manager.'}, headers=headers)
	manage = client.post(f"/stores/{shop['other_store_id']}/members", json={'user_id': str(shop['new_user_id']), 'role': 'manager'}, headers=headers)

	assert edit.status_code == 200
	assert manage.status_code == 403


def test_owner_can_list_members_without_private_data_and_with_pagination(client, shop):
	path = f"/stores/{shop['store_id']}/members"
	headers = headers_for(shop['owner_id'])
	response = client.get(path, headers=headers)

	assert response.status_code == 200
	assert response.json() == [{'user_id': str(shop['manager_id']), 'username': 'manager', 'role': 'manager'}, {'user_id': str(shop['owner_id']), 'username': 'owner', 'role': 'owner'}]
	assert client.get(path, params={'limit': 1, 'offset': 0}, headers=headers).json() == response.json()[:1]
	assert client.get(path, params={'limit': 1, 'offset': 1}, headers=headers).json() == response.json()[1:]


@pytest.mark.parametrize('params', [{'limit': 0}, {'limit': 101}, {'offset': -1}])
def test_member_pagination_rejects_invalid_limits(client, shop, params):
	response = client.get(f"/stores/{shop['store_id']}/members", params=params, headers=headers_for(shop['owner_id']))

	assert response.status_code == 422


@pytest.mark.parametrize('role', ['owner', 'manager'])
def test_owner_can_add_an_existing_user_with_either_role(client, shop, role):
	response = client.post(f"/stores/{shop['store_id']}/members", json={'user_id': str(shop['new_user_id']), 'role': role}, headers=headers_for(shop['owner_id']))

	assert response.status_code == 201
	assert response.json() == {'user_id': str(shop['new_user_id']), 'username': 'maria', 'role': role}

	with SessionLocal() as db:
		assert db.get(StoreMember, (shop['store_id'], shop['new_user_id'])).role == role
		assert db.scalar(select(func.count()).select_from(User)) == 4


def test_duplicate_member_returns_conflict_without_changing_role(client, shop):
	response = client.post(f"/stores/{shop['store_id']}/members", json={'user_id': str(shop['manager_id']), 'role': 'owner'}, headers=headers_for(shop['owner_id']))

	assert response.status_code == 409

	with SessionLocal() as db:
		assert db.get(StoreMember, (shop['store_id'], shop['manager_id'])).role == 'manager'


def test_adding_unknown_user_returns_not_found(client, shop):
	response = client.post(f"/stores/{shop['store_id']}/members", json={'user_id': str(uuid4()), 'role': 'manager'}, headers=headers_for(shop['owner_id']))

	assert response.status_code == 404


@pytest.mark.parametrize('method, suffix, data', [('PATCH', '', {'name': 'Outro nome'}), ('GET', '/members', None), ('POST', '/members', {'role': 'manager'}), ('PATCH', '/members/{target}', {'role': 'manager'}), ('DELETE', '/members/{target}', None)])
def test_operations_on_unknown_store_return_not_found(client, shop, method, suffix, data):
	suffix = suffix.format(target=shop['manager_id'])

	if method == 'POST':
		data = {**data, 'user_id': str(shop['new_user_id'])}

	response = client.request(method, f'/stores/{uuid4()}{suffix}', json=data, headers=headers_for(shop['owner_id']))

	assert response.status_code == 404


@pytest.mark.parametrize('method', ['PATCH', 'DELETE'])
@pytest.mark.parametrize('existing_user', [True, False])
def test_missing_membership_returns_not_found(client, shop, method, existing_user):
	if existing_user:
		user_id = shop['new_user_id']
	else:
		user_id = uuid4()

	response = client.request(method, f"/stores/{shop['store_id']}/members/{user_id}", json={'role': 'manager'}, headers=headers_for(shop['owner_id']))

	assert response.status_code == 404


@pytest.mark.parametrize('method', ['POST', 'PATCH'])
def test_invalid_role_is_rejected(client, shop, method):
	path = f"/stores/{shop['store_id']}/members"
	data = {'role': 'admin'}

	if method == 'POST':
		data['user_id'] = str(shop['new_user_id'])
	else:
		path += f"/{shop['manager_id']}"

	response = client.request(method, path, json=data, headers=headers_for(shop['owner_id']))

	assert response.status_code == 422


def test_owner_can_promote_manager(client, shop):
	response = client.patch(f"/stores/{shop['store_id']}/members/{shop['manager_id']}", json={'role': 'owner'}, headers=headers_for(shop['owner_id']))

	assert response.status_code == 200
	assert response.json() == {'user_id': str(shop['manager_id']), 'username': 'manager', 'role': 'owner'}
	assert client.get(f"/stores/{shop['store_id']}/members", headers=headers_for(shop['manager_id'])).status_code == 200


def test_owner_can_remove_manager_without_deleting_user(client, shop):
	response = client.delete(f"/stores/{shop['store_id']}/members/{shop['manager_id']}", headers=headers_for(shop['owner_id']))

	assert response.status_code == 204
	assert response.content == b''

	with SessionLocal() as db:
		assert db.get(StoreMember, (shop['store_id'], shop['manager_id'])) is None
		assert db.get(User, shop['manager_id']) is not None


@pytest.mark.parametrize('method', ['PATCH', 'DELETE'])
def test_last_owner_cannot_be_demoted_or_removed(client, shop, method):
	response = client.request(method, f"/stores/{shop['store_id']}/members/{shop['owner_id']}", json={'role': 'manager'}, headers=headers_for(shop['owner_id']))

	assert response.status_code == 409
	assert response.json() == {'detail': 'A loja precisa manter pelo menos um owner.'}

	with SessionLocal() as db:
		assert db.get(StoreMember, (shop['store_id'], shop['owner_id'])).role == 'owner'


def test_keeping_last_owner_role_is_allowed(client, shop):
	response = client.patch(f"/stores/{shop['store_id']}/members/{shop['owner_id']}", json={'role': 'owner'}, headers=headers_for(shop['owner_id']))

	assert response.status_code == 200


@pytest.mark.parametrize('method', ['PATCH', 'DELETE'])
def test_owner_can_leave_when_another_owner_remains_and_old_token_loses_owner_permissions(client, shop, method):
	headers = headers_for(shop['owner_id'])
	added = client.post(f"/stores/{shop['store_id']}/members", json={'user_id': str(shop['new_user_id']), 'role': 'owner'}, headers=headers)
	assert added.status_code == 201
	response = client.request(method, f"/stores/{shop['store_id']}/members/{shop['owner_id']}", json={'role': 'manager'}, headers=headers)

	if method == 'PATCH':
		assert response.status_code == 200
		assert client.patch(f"/stores/{shop['store_id']}", json={'description': 'Ainda sou manager.'}, headers=headers).status_code == 200
	else:
		assert response.status_code == 204
		assert client.patch(f"/stores/{shop['store_id']}", json={'description': 'Sem vínculo.'}, headers=headers).status_code == 403

	assert client.get(f"/stores/{shop['store_id']}/members", headers=headers).status_code == 403
	assert client.get(f"/stores/{shop['store_id']}/members", headers=headers_for(shop['new_user_id'])).status_code == 200


@pytest.mark.parametrize('method', ['PATCH', 'DELETE'])
def test_simultaneous_owner_changes_cannot_leave_store_without_owner(client, shop, method):
	added = client.post(f"/stores/{shop['store_id']}/members", json={'user_id': str(shop['new_user_id']), 'role': 'owner'}, headers=headers_for(shop['owner_id']))
	assert added.status_code == 201
	barrier = Barrier(2)

	def leave(user_id):
		with TestClient(app, base_url='https://api.noma.test') as concurrent_client:
			barrier.wait(timeout=5)
			return concurrent_client.request(method, f"/stores/{shop['store_id']}/members/{user_id}", json={'role': 'manager'}, headers=headers_for(user_id))

	with ThreadPoolExecutor(max_workers=2) as executor:
		responses = list(executor.map(leave, [shop['owner_id'], shop['new_user_id']]))

	if method == 'PATCH':
		assert sorted(response.status_code for response in responses) == [200, 409]
	else:
		assert sorted(response.status_code for response in responses) == [204, 409]

	with SessionLocal() as db:
		assert db.scalar(select(func.count()).select_from(StoreMember).where(StoreMember.store_id == shop['store_id'], StoreMember.role == 'owner')) == 1


@pytest.mark.parametrize('method', ['PATCH', 'DELETE'])
def test_browser_preflight_allows_new_methods(client, shop, method):
	response = client.options(f"/stores/{shop['store_id']}", headers={'Origin': 'https://noma.test', 'Access-Control-Request-Method': method, 'Access-Control-Request-Headers': 'authorization,content-type'})

	assert response.status_code == 200
	assert response.headers['access-control-allow-origin'] == 'https://noma.test'
	assert method in response.headers['access-control-allow-methods']

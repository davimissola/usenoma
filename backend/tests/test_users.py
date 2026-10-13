import pytest

from app.modules.auth.security import create_access_token


@pytest.mark.parametrize('user', ['owner_id', 'manager_id', 'outsider_id', 'new_user_id'])
def test_me_returns_only_the_current_users_stores_regardless_of_role(client, shop, user):
	expected = {
		'owner_id': [{'id': str(shop['other_store_id']), 'name': 'Noma Brasil', 'slug': 'noma-brasil'}, {'id': str(shop['store_id']), 'name': 'Saint', 'slug': 'saint'}],
		'manager_id': [{'id': str(shop['store_id']), 'name': 'Saint', 'slug': 'saint'}],
		'outsider_id': [{'id': str(shop['other_store_id']), 'name': 'Noma Brasil', 'slug': 'noma-brasil'}],
		'new_user_id': [],
	}
	response = client.get('/users/me', headers={'Authorization': f"Bearer {create_access_token(shop[user])}"})

	assert response.status_code == 200
	assert set(response.json()) == {'id', 'username', 'email', 'stores'}
	assert response.json()['id'] == str(shop[user])
	assert response.json()['stores'] == expected[user]


def test_me_stops_listing_a_store_after_membership_is_removed(client, shop):
	response = client.delete(f"/stores/{shop['store_id']}/members/{shop['manager_id']}", headers={'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"})

	assert response.status_code == 204

	me = client.get('/users/me', headers={'Authorization': f"Bearer {create_access_token(shop['manager_id'])}"})

	assert me.status_code == 200
	assert me.json()['stores'] == []

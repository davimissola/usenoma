from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.main import app
from app.modules.auth.dependencies import get_current_user_id
from app.modules.auth.models import AuthSession
from app.modules.users.models import User


PASSWORD = 'UmaSenhaSegura123!'


def register(client, **changes):
	data = {'username': 'davi', 'email': 'davi@example.com', 'password': PASSWORD}
	data.update(changes)

	return client.post('/auth/register', json=data)


def test_register_stores_hashes_and_returns_bearer_token(client):
	response = register(client)

	assert response.status_code == 201
	assert set(response.json()) == {'access_token', 'token_type'}
	assert response.json()['token_type'] == 'bearer'
	assert response.headers['cache-control'] == 'no-store'

	payload = jwt.decode(response.json()['access_token'], settings.secret_key.get_secret_value(), algorithms=['HS256'])
	user_id = UUID(payload['sub'])
	remaining = payload['exp'] - datetime.now(timezone.utc).timestamp()

	assert set(payload) == {'sub', 'exp'}
	assert 1790 < remaining <= 1800

	cookie = response.headers['set-cookie']
	assert 'HttpOnly' in cookie
	assert 'Secure' in cookie
	assert 'SameSite=lax' in cookie

	with SessionLocal() as db:
		user = db.get(User, user_id)
		session = db.scalar(select(AuthSession).where(AuthSession.user_id == user_id))

		assert user.password_hash != PASSWORD
		assert user.password_hash.startswith('$argon2id$')
		assert session.token_hash != client.cookies.get('refresh_token')
		assert session.revoked is False

	me = client.get('/users/me', headers={'Authorization': f"Bearer {response.json()['access_token']}"})
	assert me.status_code == 200
	assert me.json() == {'id': str(user_id), 'username': 'davi', 'email': 'davi@example.com'}


@pytest.mark.parametrize('changes', [{'username': 'DAVI', 'email': 'other@example.com'}, {'username': 'outro', 'email': 'DAVI@example.com'}])
def test_register_rejects_duplicates_without_creating_another_session(client, changes):
	assert register(client).status_code == 201
	assert register(client, **changes).status_code == 409

	with SessionLocal() as db:
		assert db.scalar(select(func.count()).select_from(User)) == 1
		assert db.scalar(select(func.count()).select_from(AuthSession)) == 1


def test_login_uses_username_and_creates_an_independent_session(client):
	assert register(client).status_code == 201
	response = client.post('/auth/login', data={'username': 'DAVI', 'password': PASSWORD})

	assert response.status_code == 200
	assert response.json()['token_type'] == 'bearer'
	assert set(response.json()) == {'access_token', 'token_type'}
	assert client.get('/users/me', headers={'Authorization': f"Bearer {response.json()['access_token']}"}).status_code == 200

	with SessionLocal() as db:
		assert db.scalar(select(func.count()).select_from(AuthSession)) == 2

	email_login = client.post('/auth/login', data={'username': 'davi@example.com', 'password': PASSWORD})
	assert email_login.status_code == 401


@pytest.mark.parametrize('username, password', [('davi', 'senha-errada'), ('inexistente', PASSWORD)])
def test_login_returns_the_same_error_for_invalid_credentials(client, username, password):
	register(client)
	response = client.post('/auth/login', data={'username': username, 'password': password})

	assert response.status_code == 401
	assert response.json() == {'detail': 'Nome de usuário ou senha incorretos.'}


@pytest.mark.parametrize('case', ['expired', 'wrong_signature', 'wrong_algorithm', 'missing_exp', 'missing_sub', 'invalid_sub', 'malformed'])
def test_protected_route_rejects_invalid_jwt(client, case):
	payload = {'sub': str(uuid4()), 'exp': datetime.now(timezone.utc) + timedelta(minutes=30)}
	secret_key = settings.secret_key.get_secret_value()
	algorithm = 'HS256'

	if case == 'expired':
		payload['exp'] = datetime.now(timezone.utc) - timedelta(seconds=1)
	elif case == 'wrong_signature':
		secret_key = 'outra-chave-aleatoria-diferente-da-original-123456'
	elif case == 'wrong_algorithm':
		algorithm = 'HS512'
	elif case == 'missing_exp':
		payload.pop('exp')
	elif case == 'missing_sub':
		payload.pop('sub')
	elif case == 'invalid_sub':
		payload['sub'] = 'id-invalido'

	token = 'token-invalido' if case == 'malformed' else jwt.encode(payload, secret_key, algorithm=algorithm)
	response = client.get('/users/me', headers={'Authorization': f'Bearer {token}'})

	assert response.status_code == 401
	assert response.headers['www-authenticate'] == 'Bearer'


def test_jwt_validation_is_stateless_but_me_requires_an_existing_user(client):
	response = register(client)
	token = response.json()['access_token']
	user_id = get_current_user_id(token)

	with SessionLocal() as db:
		db.delete(db.get(User, user_id))
		db.commit()
		assert db.scalar(select(func.count()).select_from(AuthSession)) == 0

	assert get_current_user_id(token) == user_id
	assert client.get('/users/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401
	assert client.post('/auth/refresh').status_code == 401


def test_refresh_rotates_the_token_without_extending_the_session(client):
	register(client)
	old_token = client.cookies.get('refresh_token')

	with SessionLocal() as db:
		expires_at = db.scalar(select(AuthSession.expires_at))

	response = client.post('/auth/refresh')
	assert response.status_code == 200
	assert set(response.json()) == {'access_token', 'token_type'}
	assert client.cookies.get('refresh_token') != old_token
	assert client.get('/users/me', headers={'Authorization': f"Bearer {response.json()['access_token']}"}).status_code == 200

	with SessionLocal() as db:
		assert db.scalar(select(func.count()).select_from(AuthSession)) == 1
		assert db.scalar(select(AuthSession.expires_at)) == expires_at

	assert client.post('/auth/refresh', headers={'Cookie': f'refresh_token={old_token}'}).status_code == 401
	assert client.post('/auth/refresh').status_code == 200


def test_expired_refresh_session_cannot_issue_an_access_token(client):
	register(client)

	with SessionLocal() as db:
		session = db.scalar(select(AuthSession))
		session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
		db.commit()

	assert client.post('/auth/refresh').status_code == 401


def test_logout_revokes_only_the_current_refresh_session(client):
	response = register(client)
	access_token = response.json()['access_token']
	refresh_token = client.cookies.get('refresh_token')

	with TestClient(app, base_url='https://api.noma.test', headers={'Origin': 'https://noma.test'}) as other_client:
		assert other_client.post('/auth/login', data={'username': 'davi', 'password': PASSWORD}).status_code == 200
		assert client.post('/auth/logout').status_code == 204
		assert client.cookies.get('refresh_token') is None
		assert client.post('/auth/refresh', headers={'Cookie': f'refresh_token={refresh_token}'}).status_code == 401
		assert other_client.post('/auth/refresh').status_code == 200

	assert client.post('/auth/logout').status_code == 204
	assert client.get('/users/me', headers={'Authorization': f'Bearer {access_token}'}).status_code == 200


@pytest.mark.parametrize('origin', ['https://site-malicioso.test', 'null', ''])
def test_cookie_operations_reject_untrusted_or_missing_origins(client, origin):
	register(client)
	response = client.post('/auth/logout', headers={'Origin': origin})

	assert response.status_code == 403
	assert client.post('/auth/refresh').status_code == 200


def test_simultaneous_refresh_requests_cannot_consume_the_same_token_twice(client):
	register(client)
	refresh_token = client.cookies.get('refresh_token')

	def refresh_once():
		with TestClient(app, base_url='https://api.noma.test', headers={'Origin': 'https://noma.test'}) as concurrent_client:
			return concurrent_client.post('/auth/refresh', headers={'Cookie': f'refresh_token={refresh_token}'})

	with ThreadPoolExecutor(max_workers=2) as executor:
		responses = list(executor.map(lambda _: refresh_once(), range(2)))

	assert sorted(response.status_code for response in responses) == [200, 401]


def test_authentication_requires_bearer_and_refresh_cookies(client):
	assert client.get('/users/me').status_code == 401
	assert client.post('/auth/refresh').status_code == 401

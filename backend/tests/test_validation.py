import pytest
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.modules.auth.models import AuthSession
from app.modules.users.models import User


PASSWORD = 'SenhaQueNaoPodeAparecerNaResposta!'


@pytest.mark.parametrize('data', [{'username': 'davi', 'email': 'davi@example.com', 'password': 'curta'}, {'username': 'davi', 'email': 'email-invalido', 'password': PASSWORD}, {'email': 'davi@example.com', 'password': PASSWORD}, [{'password': PASSWORD}]])
def test_invalid_register_does_not_echo_password_or_create_records(client, data):
	response = client.post('/auth/register', json=data)

	assert response.status_code == 422
	assert PASSWORD not in response.text
	assert 'curta' not in response.text

	errors = response.json()['detail']
	assert errors

	for error in errors:
		assert 'input' not in error
		assert 'ctx' not in error
		assert error['loc'][0] == 'body'
		assert isinstance(error['msg'], str)

	with SessionLocal() as db:
		assert db.scalar(select(func.count()).select_from(User)) == 0
		assert db.scalar(select(func.count()).select_from(AuthSession)) == 0

import os
from pathlib import Path
from secrets import token_urlsafe

import pytest
from sqlalchemy.engine import make_url


test_database_url = os.environ.get('TEST_DATABASE_URL')

if not test_database_url:
	raise pytest.UsageError('Defina TEST_DATABASE_URL para um PostgreSQL local exclusivo de testes, com nome terminado em _test.')

test_url = make_url(test_database_url)

if test_url.get_backend_name() != 'postgresql' or test_url.host not in {'localhost', '127.0.0.1'} or not (test_url.database or '').endswith('_test'):
	raise pytest.UsageError('Os testes exigem PostgreSQL local e banco com nome terminado em _test. Não use o banco da aplicação.')

os.environ['DATABASE_URL'] = test_database_url
os.environ['SECRET_KEY'] = token_urlsafe(48)
os.environ['FRONTEND_URL'] = 'https://noma.test'
os.environ['COOKIE_SECURE'] = 'true'

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.database import engine
from app.main import app


@pytest.fixture(scope='session', autouse=True)
def migrate_database():
	config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
	command.upgrade(config, 'head')

	yield

	engine.dispose()


@pytest.fixture(autouse=True)
def clean_database(migrate_database):
	with engine.begin() as connection:
		connection.exec_driver_sql('TRUNCATE TABLE app.auth_sessions, app.users')


@pytest.fixture
def client():
	with TestClient(app, base_url='https://api.noma.test', headers={'Origin': 'https://noma.test'}) as test_client:
		yield test_client

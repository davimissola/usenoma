import os
from decimal import Decimal
from pathlib import Path
from secrets import token_urlsafe
from unittest.mock import Mock

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

from app.core.database import SessionLocal, engine
from app.core.config import settings
from app.main import app
from app.modules.products import storage as product_storage_module
from app.modules.products.models import Product
from app.modules.stores.models import Store, StoreMember
from app.modules.users.models import User


@pytest.fixture(scope='session', autouse=True)
def migrate_database():
	config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
	command.upgrade(config, 'head')

	yield

	engine.dispose()


@pytest.fixture(autouse=True)
def clean_database(migrate_database):
	with engine.begin() as connection:
		connection.exec_driver_sql('TRUNCATE TABLE app.product_images, app.product_sizes, app.products, app.store_image_variants, app.store_images, app.store_members, app.stores, app.auth_sessions, app.users')


@pytest.fixture
def client():
	with TestClient(app, base_url='https://api.noma.test', headers={'Origin': 'https://noma.test'}) as test_client:
		yield test_client


@pytest.fixture
def shop():
	with SessionLocal() as db:
		store = Store(name='Saint', slug='saint', description='Streetwear.')
		other_store = Store(name='Noma Brasil', slug='noma-brasil')
		owner = User(username='owner', email='owner@example.com', password_hash='hash-de-teste')
		manager = User(username='manager', email='manager@example.com', password_hash='hash-de-teste')
		outsider = User(username='outsider', email='outsider@example.com', password_hash='hash-de-teste')
		new_user = User(username='maria', email='maria@example.com', password_hash='hash-de-teste')
		db.add_all([store, other_store, owner, manager, outsider, new_user])
		db.flush()
		db.add_all([
			StoreMember(store_id=store.id, user_id=owner.id, role='owner'),
			StoreMember(store_id=store.id, user_id=manager.id, role='manager'),
			StoreMember(store_id=other_store.id, user_id=outsider.id, role='owner'),
			StoreMember(store_id=other_store.id, user_id=owner.id, role='manager'),
		])
		db.commit()

		return {'store_id': store.id, 'other_store_id': other_store.id, 'owner_id': owner.id, 'manager_id': manager.id, 'outsider_id': outsider.id, 'new_user_id': new_user.id}


@pytest.fixture
def product(shop):
	with SessionLocal() as db:
		row = Product(store_id=shop['store_id'], name='Camiseta', price=Decimal('149.90'), description='Algodão.')
		db.add(row)
		db.commit()
		return row.id


@pytest.fixture
def product_storage(monkeypatch):
	monkeypatch.setattr(settings, 'supabase_url', 'https://product-project.supabase.co')
	monkeypatch.setattr(settings, 'supabase_storage_bucket', 'store-media')
	upload, delete = Mock(), Mock()
	monkeypatch.setattr(product_storage_module, 'upload_image', upload)
	monkeypatch.setattr(product_storage_module, 'delete_image', delete)
	return upload, delete

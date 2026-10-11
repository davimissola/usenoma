from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.stores.models import Store, StoreMember
from app.modules.users.models import User


@pytest.fixture
def store_data():
	with SessionLocal() as db:
		store = Store(name='Saint', slug='saint', description='Loja de streetwear.')
		other_store = Store(name='Noma Brasil', slug='noma-brasil')
		user = User(username='davi', email='davi@example.com', password_hash='hash-de-teste')
		other_user = User(username='maria', email='maria@example.com', password_hash='hash-de-teste')

		db.add_all([store, other_store, user, other_user])
		db.commit()

		return store.id, other_store.id, user.id, other_user.id


def test_users_can_manage_multiple_stores_with_different_roles(store_data):
	store_id, other_store_id, user_id, other_user_id = store_data

	with SessionLocal() as db:
		db.add_all([
			StoreMember(store_id=store_id, user_id=user_id, role='owner'),
			StoreMember(store_id=store_id, user_id=other_user_id, role='manager'),
			StoreMember(store_id=other_store_id, user_id=user_id, role='manager'),
		])
		db.commit()

		members = db.execute(select(StoreMember.store_id, StoreMember.user_id, StoreMember.role)).all()

		assert set(members) == {(store_id, user_id, 'owner'), (store_id, other_user_id, 'manager'), (other_store_id, user_id, 'manager')}
		assert db.get(Store, other_store_id).description is None


def test_store_slug_is_unique(store_data):
	with SessionLocal() as db:
		db.add(Store(name='Outra Saint', slug='saint'))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'uq_stores_slug'
		assert db.scalar(select(func.count()).select_from(Store)) == 2


@pytest.mark.parametrize('slug', ['Saint', 'loja teste', ''])
def test_store_slug_rejects_noncanonical_values(slug):
	with SessionLocal() as db:
		db.add(Store(name='Loja teste', slug=slug))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'ck_stores_slug'


@pytest.mark.parametrize('name', ['', '   '])
def test_store_name_cannot_be_empty(name):
	with SessionLocal() as db:
		db.add(Store(name=name, slug='loja-teste'))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'ck_stores_name'


def test_store_member_pair_is_unique_even_with_another_role(store_data):
	store_id, _, user_id, _ = store_data

	with SessionLocal() as db:
		db.add(StoreMember(store_id=store_id, user_id=user_id, role='owner'))
		db.commit()

	with SessionLocal() as db:
		db.add(StoreMember(store_id=store_id, user_id=user_id, role='manager'))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'store_members_pkey'
		assert db.get(StoreMember, (store_id, user_id)).role == 'owner'


@pytest.mark.parametrize('role', ['admin', 'OWNER'])
def test_store_member_rejects_unknown_roles(store_data, role):
	store_id, _, user_id, _ = store_data

	with SessionLocal() as db:
		db.add(StoreMember(store_id=store_id, user_id=user_id, role=role))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'ck_store_members_role'


def test_store_member_requires_a_role(store_data):
	store_id, _, user_id, _ = store_data

	with SessionLocal() as db:
		db.add(StoreMember(store_id=store_id, user_id=user_id))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.sqlstate == '23502'
		assert error.value.orig.diag.column_name == 'role'


@pytest.mark.parametrize('field, constraint', [('store_id', 'fk_store_members_store_id'), ('user_id', 'fk_store_members_user_id')])
def test_store_member_requires_existing_records(store_data, field, constraint):
	store_id, _, user_id, _ = store_data
	data = {'store_id': store_id, 'user_id': user_id, 'role': 'manager'}
	data[field] = uuid4()

	with SessionLocal() as db:
		db.add(StoreMember(**data))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == constraint


def test_deleting_store_removes_only_its_memberships(store_data):
	store_id, other_store_id, user_id, other_user_id = store_data

	with SessionLocal() as db:
		db.add_all([
			StoreMember(store_id=store_id, user_id=user_id, role='owner'),
			StoreMember(store_id=store_id, user_id=other_user_id, role='manager'),
			StoreMember(store_id=other_store_id, user_id=user_id, role='manager'),
		])
		db.commit()

		db.delete(db.get(Store, store_id))
		db.commit()

		assert db.get(Store, store_id) is None
		assert db.scalar(select(func.count()).select_from(StoreMember)) == 1
		assert db.get(StoreMember, (other_store_id, user_id)).role == 'manager'
		assert db.scalar(select(func.count()).select_from(User)) == 2


def test_user_delete_requires_removing_memberships_first(store_data):
	store_id, _, user_id, _ = store_data

	with SessionLocal() as db:
		db.add(StoreMember(store_id=store_id, user_id=user_id, role='owner'))
		db.commit()
		db.delete(db.get(User, user_id))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'fk_store_members_user_id'
		assert db.get(User, user_id) is not None
		assert db.get(StoreMember, (store_id, user_id)).role == 'owner'

		db.delete(db.get(StoreMember, (store_id, user_id)))
		db.commit()
		db.delete(db.get(User, user_id))
		db.commit()

		assert db.get(User, user_id) is None
		assert db.get(Store, store_id) is not None

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.addresses.models import UserAddress
from app.modules.users.models import User


def test_address_requires_an_existing_user(address_data):
	with SessionLocal() as db:
		db.add(UserAddress(user_id=uuid4(), **address_data))
		with pytest.raises(IntegrityError) as error:
			db.commit()
		db.rollback()
		assert error.value.orig.diag.constraint_name == 'fk_user_addresses_user_id'


def test_partial_index_allows_many_addresses_but_only_one_default_per_user(shop, address_data):
	with SessionLocal() as db:
		db.add_all([
			UserAddress(user_id=shop['new_user_id'], **address_data, is_default=True),
			UserAddress(user_id=shop['new_user_id'], **address_data),
			UserAddress(user_id=shop['new_user_id'], **address_data),
			UserAddress(user_id=shop['outsider_id'], **address_data, is_default=True),
		])
		db.commit()
		db.add(UserAddress(user_id=shop['new_user_id'], **address_data, is_default=True))
		with pytest.raises(IntegrityError) as error:
			db.commit()
		db.rollback()
		assert error.value.orig.diag.constraint_name == 'uq_user_addresses_default'
		assert len(db.scalars(select(UserAddress)).all()) == 4


def test_database_rejects_concurrent_defaults_even_without_service_lock(shop, address_data):
	barrier = Barrier(2)
	def insert_default(_):
		with SessionLocal() as db:
			db.add(UserAddress(user_id=shop['new_user_id'], **address_data, is_default=True))
			barrier.wait(timeout=10)
			try:
				db.commit()
				return True
			except IntegrityError as error:
				db.rollback()
				assert error.orig.diag.constraint_name == 'uq_user_addresses_default'
				return False

	with ThreadPoolExecutor(max_workers=2) as executor:
		assert sorted(executor.map(insert_default, range(2))) == [False, True]
	with SessionLocal() as db:
		assert len(db.scalars(select(UserAddress).where(UserAddress.is_default.is_(True))).all()) == 1


def test_deleting_user_cascades_addresses(shop, address_data):
	with SessionLocal() as db:
		db.add(UserAddress(user_id=shop['new_user_id'], **address_data, is_default=True))
		db.commit()
		db.delete(db.get(User, shop['new_user_id']))
		db.commit()
		assert db.scalars(select(UserAddress)).all() == []


@pytest.mark.parametrize('field, value, constraint', [
	('recipient_name', ' ', 'ck_user_addresses_recipient_name'), ('postal_code', '123', 'ck_user_addresses_postal_code'),
	('street', ' ', 'ck_user_addresses_street'), ('number', '', 'ck_user_addresses_number'), ('complement', ' ', 'ck_user_addresses_complement'),
	('neighborhood', ' ', 'ck_user_addresses_neighborhood'), ('city', ' ', 'ck_user_addresses_city'),
	('state', 'XX', 'ck_user_addresses_state'), ('phone', '123', 'ck_user_addresses_phone'),
])
def test_address_constraints_also_protect_direct_database_writes(shop, address_data, field, value, constraint):
	with SessionLocal() as db:
		db.add(UserAddress(user_id=shop['new_user_id'], **{**address_data, field: value}))
		with pytest.raises(IntegrityError) as error:
			db.commit()
		db.rollback()
		assert error.value.orig.diag.constraint_name == constraint

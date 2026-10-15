from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.cart.models import Cart, CartItem
from app.modules.products.models import Product
from app.modules.users.models import User


@pytest.fixture
def cart_data(shop, product):
	with SessionLocal() as db:
		cart = Cart(user_id=shop['new_user_id'])
		db.add(cart)
		db.commit()
		return cart.id, product


def test_user_can_have_only_one_cart(shop):
	with SessionLocal() as db:
		db.add(Cart(user_id=shop['new_user_id']))
		db.commit()
		db.add(Cart(user_id=shop['new_user_id']))
		with pytest.raises(IntegrityError) as error:
			db.commit()
		db.rollback()
		assert error.value.orig.diag.constraint_name == 'uq_carts_user_id'


def test_cart_requires_an_existing_user():
	with SessionLocal() as db:
		db.add(Cart(user_id=uuid4()))
		with pytest.raises(IntegrityError) as error:
			db.commit()
		db.rollback()
		assert error.value.orig.diag.constraint_name == 'fk_carts_user_id'


def test_product_and_size_are_unique_within_cart(cart_data):
	cart_id, product_id = cart_data
	with SessionLocal() as db:
		db.add(CartItem(cart_id=cart_id, product_id=product_id, size='M', quantity=1))
		db.commit()
		db.add(CartItem(cart_id=cart_id, product_id=product_id, size='M', quantity=2))
		with pytest.raises(IntegrityError) as error:
			db.commit()
		db.rollback()
		assert error.value.orig.diag.constraint_name == 'uq_cart_items_cart_product_size'


@pytest.mark.parametrize('field, value, constraint', [('cart_id', None, 'not_null'), ('cart_id', 'missing', 'fk_cart_items_cart_id'), ('product_id', 'missing', 'fk_cart_items_product_id'), ('quantity', 0, 'ck_cart_items_quantity'), ('quantity', -1, 'ck_cart_items_quantity'), ('quantity', None, 'not_null'), ('size', '', 'ck_cart_items_size'), ('size', '   ', 'ck_cart_items_size')])
def test_cart_item_constraints(cart_data, field, value, constraint):
	cart_id, product_id = cart_data
	if value == 'missing':
		value = uuid4()
	data = {'cart_id': cart_id, 'product_id': product_id, 'size': 'M', 'quantity': 1}
	data[field] = value
	with SessionLocal() as db:
		db.add(CartItem(**data))
		with pytest.raises(IntegrityError) as error:
			db.commit()
		db.rollback()
		if constraint == 'not_null':
			assert error.value.orig.sqlstate == '23502'
		else:
			assert error.value.orig.diag.constraint_name == constraint


def test_deleting_cart_cascades_only_its_items(cart_data, shop):
	cart_id, product_id = cart_data
	with SessionLocal() as db:
		other = Cart(user_id=shop['outsider_id'])
		db.add(other)
		db.flush()
		db.add_all([CartItem(cart_id=cart_id, product_id=product_id, size='M', quantity=1), CartItem(cart_id=other.id, product_id=product_id, size='M', quantity=2)])
		db.commit()
		db.delete(db.get(Cart, cart_id))
		db.commit()
		assert db.get(Cart, cart_id) is None
		assert db.get(Product, product_id) is not None
		assert db.scalars(select(CartItem.cart_id)).all() == [other.id]


def test_deleting_user_cascades_cart_and_items(cart_data, shop):
	cart_id, product_id = cart_data
	with SessionLocal() as db:
		db.add(CartItem(cart_id=cart_id, product_id=product_id, size='M', quantity=1))
		db.commit()
		db.delete(db.get(User, shop['new_user_id']))
		db.commit()
		assert db.get(Cart, cart_id) is None
		assert db.scalars(select(CartItem)).all() == []
		assert db.get(Product, product_id) is not None


def test_deleted_products_keep_distinct_cart_items_even_with_same_size(cart_data, shop):
	cart_id, product_id = cart_data
	with SessionLocal() as db:
		other = Product(store_id=shop['store_id'], name='Outro produto', price=Decimal('10.00'))
		db.add(other)
		db.flush()
		db.add_all([CartItem(cart_id=cart_id, product_id=product_id, size='M', quantity=1), CartItem(cart_id=cart_id, product_id=other.id, size='M', quantity=2)])
		db.commit()
		db.delete(db.get(Product, product_id))
		db.delete(other)
		db.commit()
		items = db.scalars(select(CartItem)).all()
		assert len(items) == 2
		assert all(item.product_id is None for item in items)


def test_cart_models_do_not_persist_price_or_store():
	assert set(Cart.__table__.columns.keys()) == {'id', 'user_id', 'updated_at'}
	assert set(CartItem.__table__.columns.keys()) == {'id', 'cart_id', 'product_id', 'size', 'quantity'}

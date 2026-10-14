from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.products.models import Product, ProductImage, ProductSize
from app.modules.stores.models import Store


@pytest.fixture
def product_data():
	with SessionLocal() as db:
		store = Store(name='Saint', slug='saint')
		other_store = Store(name='Noma Brasil', slug='noma-brasil')
		db.add_all([store, other_store])
		db.flush()

		product = Product(store_id=store.id, name='Camiseta Oversized', price=Decimal('149.90'))
		other_product = Product(store_id=other_store.id, name='Camiseta Classic', price=Decimal('99.90'))
		db.add_all([product, other_product])
		db.commit()

		return store.id, other_store.id, product.id, other_product.id


@pytest.mark.parametrize('price', [Decimal('0.00'), Decimal('0.10') + Decimal('0.20'), Decimal('99999999.99')])
def test_price_round_trips_as_decimal_without_losing_cents(product_data, price):
	_, _, product_id, _ = product_data

	with SessionLocal() as db:
		product = db.get(Product, product_id)
		product.price = price
		db.commit()
		db.expire_all()
		stored = db.get(Product, product_id)

		assert isinstance(stored.price, Decimal)
		assert stored.price == price
		assert stored.description is None


@pytest.mark.parametrize('price', [Decimal('-0.01'), Decimal('NaN')])
def test_price_rejects_negative_and_nan_values(product_data, price):
	store_id, _, _, _ = product_data

	with SessionLocal() as db:
		db.add(Product(store_id=store_id, name='Produto inválido', price=price))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'ck_products_price'
		assert db.scalar(select(func.count()).select_from(Product)) == 2


@pytest.mark.parametrize('name', ['', '   '])
def test_product_name_cannot_be_blank(product_data, name):
	store_id, _, _, _ = product_data

	with SessionLocal() as db:
		db.add(Product(store_id=store_id, name=name, price=Decimal('10.00')))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'ck_products_name'


def test_product_requires_an_existing_store():
	with SessionLocal() as db:
		db.add(Product(store_id=uuid4(), name='Camiseta', price=Decimal('10.00')))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'fk_products_store_id'


@pytest.mark.parametrize('model, data, constraint', [(ProductSize, {'size': 'M', 'available': True}, 'fk_product_sizes_product_id'), (ProductImage, {'storage_path': 'products/missing.webp', 'position': 1}, 'fk_product_images_product_id')])
def test_sizes_and_images_require_an_existing_product(model, data, constraint):
	with SessionLocal() as db:
		db.add(model(product_id=uuid4(), **data))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == constraint


def test_size_can_be_disabled_without_removing_its_record(product_data):
	_, _, product_id, _ = product_data

	with SessionLocal() as db:
		db.add(ProductSize(product_id=product_id, size='M', available=True))
		db.commit()
		size = db.get(ProductSize, (product_id, 'M'))
		size.available = False
		db.commit()
		db.expire_all()

		assert db.get(ProductSize, (product_id, 'M')).available is False
		assert db.scalar(select(func.count()).select_from(ProductSize)) == 1


def test_size_is_unique_within_each_product(product_data):
	_, _, product_id, _ = product_data

	with SessionLocal() as db:
		db.add(ProductSize(product_id=product_id, size='M', available=True))
		db.commit()

	with SessionLocal() as db:
		db.add(ProductSize(product_id=product_id, size='M', available=False))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'product_sizes_pkey'
		assert db.get(ProductSize, (product_id, 'M')).available is True


def test_different_products_can_have_the_same_size_and_image_position(product_data):
	_, _, product_id, other_product_id = product_data

	with SessionLocal() as db:
		db.add_all([
			ProductSize(product_id=product_id, size='M', available=True),
			ProductSize(product_id=other_product_id, size='M', available=False),
			ProductImage(product_id=product_id, storage_path='products/first.webp', position=1),
			ProductImage(product_id=other_product_id, storage_path='products/second.webp', position=1),
		])
		db.commit()

		assert db.scalar(select(func.count()).select_from(ProductSize)) == 2
		assert db.scalar(select(func.count()).select_from(ProductImage)) == 2


@pytest.mark.parametrize('size', ['', '   '])
def test_size_cannot_be_blank(product_data, size):
	_, _, product_id, _ = product_data

	with SessionLocal() as db:
		db.add(ProductSize(product_id=product_id, size=size, available=True))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'ck_product_sizes_size'


def test_size_availability_cannot_be_null(product_data):
	_, _, product_id, _ = product_data

	with SessionLocal() as db:
		db.add(ProductSize(product_id=product_id, size='M', available=None))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.sqlstate == '23502'
		assert error.value.orig.diag.column_name == 'available'


def test_product_accepts_five_images_but_rejects_a_sixth(product_data):
	_, _, product_id, _ = product_data

	with SessionLocal() as db:
		db.add_all([ProductImage(product_id=product_id, storage_path=f'products/{position}.webp', position=position) for position in range(1, 6)])
		db.commit()
		positions = db.scalars(select(ProductImage.position).where(ProductImage.product_id == product_id).order_by(ProductImage.position)).all()
		assert positions == [1, 2, 3, 4, 5]

		db.add(ProductImage(product_id=product_id, storage_path='products/6.webp', position=6))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'ck_product_images_position'
		assert db.scalar(select(func.count()).select_from(ProductImage)) == 5


def test_image_position_is_unique_within_each_product(product_data):
	_, _, product_id, _ = product_data

	with SessionLocal() as db:
		db.add(ProductImage(product_id=product_id, storage_path='products/first.webp', position=1))
		db.commit()
		db.add(ProductImage(product_id=product_id, storage_path='products/repeated.webp', position=1))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == 'uq_product_images_product_position'
		assert db.scalar(select(func.count()).select_from(ProductImage)) == 1


@pytest.mark.parametrize('field, value, constraint', [('position', 0, 'ck_product_images_position'), ('position', -1, 'ck_product_images_position'), ('storage_path', '', 'ck_product_images_storage_path'), ('storage_path', '   ', 'ck_product_images_storage_path')])
def test_image_rejects_invalid_position_or_path(product_data, field, value, constraint):
	_, _, product_id, _ = product_data
	data = {'product_id': product_id, 'storage_path': 'products/image.webp', 'position': 1}
	data[field] = value

	with SessionLocal() as db:
		db.add(ProductImage(**data))

		with pytest.raises(IntegrityError) as error:
			db.commit()

		db.rollback()
		assert error.value.orig.diag.constraint_name == constraint


def test_deleting_product_cascades_only_its_sizes_and_images(product_data):
	store_id, _, product_id, other_product_id = product_data

	with SessionLocal() as db:
		db.add_all([
			ProductSize(product_id=product_id, size='M', available=False),
			ProductSize(product_id=other_product_id, size='M', available=True),
			ProductImage(product_id=product_id, storage_path='products/first.webp', position=1),
			ProductImage(product_id=other_product_id, storage_path='products/second.webp', position=1),
		])
		db.commit()
		db.delete(db.get(Product, product_id))
		db.commit()

		assert db.get(Product, product_id) is None
		assert db.get(Store, store_id) is not None
		assert db.get(Product, other_product_id) is not None
		assert db.scalar(select(func.count()).select_from(ProductSize)) == 1
		assert db.get(ProductSize, (other_product_id, 'M')).available is True
		assert db.scalars(select(ProductImage.product_id)).all() == [other_product_id]


def test_deleting_store_cascades_only_its_products_and_children(product_data):
	store_id, other_store_id, product_id, other_product_id = product_data

	with SessionLocal() as db:
		db.add_all([
			ProductSize(product_id=product_id, size='M', available=True),
			ProductSize(product_id=other_product_id, size='M', available=True),
			ProductImage(product_id=product_id, storage_path='products/first.webp', position=1),
			ProductImage(product_id=other_product_id, storage_path='products/second.webp', position=1),
		])
		db.commit()
		db.delete(db.get(Store, store_id))
		db.commit()

		assert db.get(Store, store_id) is None
		assert db.get(Product, product_id) is None
		assert db.get(Store, other_store_id) is not None
		assert db.get(Product, other_product_id) is not None
		assert db.scalars(select(ProductSize.product_id)).all() == [other_product_id]
		assert db.scalars(select(ProductImage.product_id)).all() == [other_product_id]

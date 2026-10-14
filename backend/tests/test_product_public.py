from decimal import Decimal

import pytest
from sqlalchemy import event

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.modules.products.models import Product, ProductImage, ProductSize


def test_public_product_has_available_sizes_ordered_images_and_no_internal_fields(client, shop, product, product_storage):
	with SessionLocal() as db:
		db.add_all([
			ProductSize(product_id=product, size='G', available=False),
			ProductSize(product_id=product, size='M', available=True),
			ProductImage(product_id=product, storage_path=f'stores/{shop["store_id"]}/products/{product}/second/large.webp', position=2),
			ProductImage(product_id=product, storage_path=f'stores/{shop["store_id"]}/products/{product}/first/large.webp', position=1),
		])
		db.commit()

	response = client.get(f'/products/{product}')
	assert response.status_code == 200
	data = response.json()
	assert data['price'] == '149.90'
	assert data['sizes'] == [{'size': 'M', 'available': True}]
	assert [image['position'] for image in data['images']] == [1, 2]
	assert data['images'][0]['variants']['card']['url'].endswith('/first/card.webp')
	assert data['images'][0]['variants']['large']['url'].endswith('/first/large.webp')
	assert set(data) == {'id', 'store_id', 'name', 'price', 'description', 'sizes', 'images'}
	assert 'storage_path' not in response.text
	assert 'user_id' not in response.text
	assert 'role' not in response.text
	assert client.get(f"/stores/{shop['store_id']}/products").json() == [data]
	product_storage[0].assert_not_called()
	product_storage[1].assert_not_called()


def test_store_product_list_is_public_paginated_and_isolated(client, shop, product):
	with SessionLocal() as db:
		second = Product(store_id=shop['store_id'], name='Outra camiseta', price=Decimal('99.00'))
		other = Product(store_id=shop['other_store_id'], name='Outro catálogo', price=Decimal('50.00'))
		db.add_all([second, other])
		db.commit()
		expected = sorted([str(product), str(second.id)])

	base = f"/stores/{shop['store_id']}/products"
	data = client.get(base).json()
	assert [row['id'] for row in data] == expected
	assert all(row['store_id'] == str(shop['store_id']) for row in data)
	assert all(row['sizes'] == [] and row['images'] == [] for row in data)
	assert [client.get(f'{base}?offset={offset}&limit=1').json()[0]['id'] for offset in [0, 1]] == expected
	assert client.get(f'{base}?offset=2').json() == []


@pytest.mark.parametrize('params', ['offset=-1', 'limit=0', 'limit=101'])
def test_product_pagination_rejects_invalid_values(client, shop, params):
	assert client.get(f"/stores/{shop['store_id']}/products?{params}").status_code == 422


def test_store_without_products_returns_empty_list(client, shop):
	assert client.get(f"/stores/{shop['store_id']}/products").json() == []


def test_listing_more_products_does_not_add_queries_per_product(client, shop, product, product_storage):
	statements = []

	def count_selects(connection, cursor, statement, parameters, context, executemany):
		if statement.lstrip().upper().startswith('SELECT'):
			statements.append(statement)

	event.listen(engine, 'before_cursor_execute', count_selects)

	try:
		assert client.get(f"/stores/{shop['store_id']}/products").status_code == 200
		initial_count = len(statements)

		with SessionLocal() as db:
			for index in range(3):
				row = Product(store_id=shop['store_id'], name=f'Camiseta {index}', price=Decimal('10.00'))
				db.add(row)
				db.flush()
				db.add(ProductSize(product_id=row.id, size='M', available=True))
				db.add(ProductImage(product_id=row.id, storage_path=f'products/{row.id}/large.webp', position=1))
			db.commit()

		statements.clear()
		response = client.get(f"/stores/{shop['store_id']}/products")
		assert response.status_code == 200
		assert len(response.json()) == 4
		assert len(statements) == initial_count
	finally:
		event.remove(engine, 'before_cursor_execute', count_selects)


def test_detail_reads_without_storage_configuration_when_product_has_no_images(client, shop, product, monkeypatch):
	monkeypatch.setattr(settings, 'supabase_url', None)
	response = client.get(f'/products/{product}')
	assert response.status_code == 200
	assert response.json()['images'] == []
	assert response.json()['sizes'] == []
	assert client.get(f"/stores/{shop['store_id']}/products").json() == [response.json()]


def test_public_catalog_default_limit_and_available_sizes(client, shop):
	with SessionLocal() as db:
		rows = [Product(store_id=shop['store_id'], name=f'Produto {index}', price=Decimal('0.00')) for index in range(21)]
		db.add_all(rows)
		db.flush()
		for row in rows:
			db.add(ProductSize(product_id=row.id, size='M', available=False))
		db.commit()
		expected = sorted(str(row.id) for row in rows)

	base = f"/stores/{shop['store_id']}/products"
	first = client.get(base).json()
	second = client.get(f'{base}?offset=20').json()
	assert [row['id'] for row in first + second] == expected
	assert len(first) == 20
	assert len(second) == 1
	assert all(row['sizes'] == [] and row['images'] == [] and row['price'] == '0.00' for row in first + second)

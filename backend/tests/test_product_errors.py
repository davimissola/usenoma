from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.auth.security import create_access_token
from app.modules.products import service
from app.modules.products.models import Product, ProductImage, ProductSize


@pytest.mark.parametrize('operation', ['create', 'update', 'add_size', 'update_size', 'remove_size', 'reorder', 'remove_image', 'delete'])
def test_failed_commit_preserves_product_sizes_images_and_storage(client, shop, product, product_storage, monkeypatch, caplog, operation):
	first_id, second_id = uuid4(), uuid4()
	with SessionLocal() as db:
		db.add(ProductSize(product_id=product, size='M', available=True))
		db.add_all([ProductImage(id=first_id, product_id=product, position=1, storage_path='products/first/large.webp'), ProductImage(id=second_id, product_id=product, position=2, storage_path='products/second/large.webp')])
		db.commit()

	base = f"/stores/{shop['store_id']}/products"
	requests = {
		'create': ('POST', base, {'name': 'Novo produto', 'price': '10.00'}),
		'update': ('PATCH', f'{base}/{product}', {'name': 'Alterado', 'price': '9.90'}),
		'add_size': ('POST', f'{base}/{product}/sizes', {'size': 'G'}),
		'update_size': ('PATCH', f'{base}/{product}/sizes/M', {'available': False}),
		'remove_size': ('DELETE', f'{base}/{product}/sizes/M', None),
		'reorder': ('PATCH', f'{base}/{product}/images/order', {'image_ids': [str(second_id), str(first_id)]}),
		'remove_image': ('DELETE', f'{base}/{product}/images/{first_id}', None),
		'delete': ('DELETE', f'{base}/{product}', None),
	}
	monkeypatch.setattr(SessionLocal.class_, 'commit', Mock(side_effect=OperationalError('SQL privado', {'password': 'senha-privada'}, Exception('erro-privado'))))
	method, path, data = requests[operation]
	response = client.request(method, path, json=data, headers={'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"})
	assert response.status_code == 503
	assert all(value not in response.text for value in ['SQL privado', 'senha-privada', 'erro-privado'])
	assert 'senha-privada' not in caplog.text
	product_storage[0].assert_not_called()
	product_storage[1].assert_not_called()

	with SessionLocal() as db:
		rows = db.scalars(select(Product)).all()
		assert len(rows) == 1
		assert rows[0].id == product
		assert rows[0].name == 'Camiseta'
		assert rows[0].price == Decimal('149.90')
		assert db.scalars(select(ProductSize.size)).all() == ['M']
		assert db.get(ProductSize, (product, 'M')).available is True
		assert [(image.id, image.position) for image in db.scalars(select(ProductImage).order_by(ProductImage.position))] == [(first_id, 1), (second_id, 2)]


@pytest.mark.parametrize('method', ['POST', 'PATCH'])
def test_response_failure_does_not_commit_a_product_write(client, shop, product, monkeypatch, method):
	monkeypatch.setattr(service, 'build_product_responses', Mock(side_effect=HTTPException(status_code=503, detail='Falha na resposta.')))
	path = f"/stores/{shop['store_id']}/products"
	if method == 'PATCH':
		path += f'/{product}'

	response = client.request(method, path, json={'name': 'Alterado', 'price': '9.90'}, headers={'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"})
	assert response.status_code == 503

	with SessionLocal() as db:
		assert len(db.scalars(select(Product)).all()) == 1
		assert db.get(Product, product).name == 'Camiseta'
		assert db.get(Product, product).price == Decimal('149.90')


def test_unconfigured_image_urls_do_not_commit_a_product_edit(client, shop, product, monkeypatch):
	with SessionLocal() as db:
		db.add(ProductImage(product_id=product, position=1, storage_path='products/image/large.webp'))
		db.commit()

	monkeypatch.setattr(settings, 'supabase_url', None)
	response = client.patch(f"/stores/{shop['store_id']}/products/{product}", json={'name': 'Alterado'}, headers={'Authorization': f"Bearer {create_access_token(shop['owner_id'])}"})
	assert response.status_code == 503

	with SessionLocal() as db:
		assert db.get(Product, product).name == 'Camiseta'

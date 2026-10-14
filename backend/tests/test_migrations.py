from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError

from app.core.database import engine


def test_models_match_the_applied_migrations():
	config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
	command.check(config)


def test_pending_product_migrations_return_safe_error_and_upgrade_restores_listing(client, shop):
	config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
	engine.dispose()

	try:
		command.downgrade(config, '0004')
		response = client.get(f"/stores/{shop['store_id']}/products")
		assert response.status_code == 503
		assert set(response.json()) == {'detail'}
		assert 'app.products' not in response.text
		assert 'SELECT' not in response.text

		command.upgrade(config, 'head')
		response = client.get(f"/stores/{shop['store_id']}/products")
		assert response.status_code == 200
		assert response.json() == []
	finally:
		command.upgrade(config, 'head')
		engine.dispose()


def test_image_position_migration_preserves_rows_and_supports_downgrade():
	config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
	store_id, product_id, image_id = uuid4(), uuid4(), uuid4()
	engine.dispose()

	try:
		command.downgrade(config, '0005')

		with engine.begin() as connection:
			connection.exec_driver_sql('INSERT INTO app.stores (id, name, slug) VALUES (%s, %s, %s)', (store_id, 'Loja existente', 'loja-existente'))
			connection.exec_driver_sql('INSERT INTO app.products (id, store_id, name, price) VALUES (%s, %s, %s, %s)', (product_id, store_id, 'Camiseta', Decimal('10.00')))
			connection.exec_driver_sql('INSERT INTO app.product_images (id, product_id, storage_path, position) VALUES (%s, %s, %s, %s)', (image_id, product_id, 'products/image/large.webp', 1))

		command.upgrade(config, 'head')

		with engine.connect() as connection:
			assert connection.exec_driver_sql("SELECT condeferrable FROM pg_constraint WHERE conrelid = 'app.product_images'::regclass AND conname = 'uq_product_images_product_position'").scalar_one() is True
			assert connection.exec_driver_sql('SELECT storage_path, position FROM app.product_images WHERE id = %s', (image_id,)).one() == ('products/image/large.webp', 1)

		command.downgrade(config, '0005')

		with engine.connect() as connection:
			assert connection.exec_driver_sql("SELECT condeferrable FROM pg_constraint WHERE conrelid = 'app.product_images'::regclass AND conname = 'uq_product_images_product_position'").scalar_one() is False
			assert connection.exec_driver_sql('SELECT position FROM app.product_images WHERE id = %s', (image_id,)).scalar_one() == 1
	finally:
		command.upgrade(config, 'head')
		engine.dispose()


def test_four_image_limit_migration_preserves_images_and_supports_downgrade(shop, product):
	config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
	image_ids = [uuid4() for _ in range(4)]
	engine.dispose()

	try:
		command.downgrade(config, '0006')
		with engine.begin() as connection:
			for position, image_id in enumerate(image_ids, 1):
				connection.exec_driver_sql('INSERT INTO app.product_images (id, product_id, storage_path, position) VALUES (%s, %s, %s, %s)', (image_id, product, f'products/{position}/large.webp', position))

		command.upgrade(config, 'head')
		with engine.connect() as connection:
			assert connection.exec_driver_sql('SELECT id FROM app.product_images ORDER BY position').scalars().all() == image_ids

		with pytest.raises(IntegrityError), engine.begin() as connection:
			connection.exec_driver_sql('INSERT INTO app.product_images (id, product_id, storage_path, position) VALUES (%s, %s, %s, %s)', (uuid4(), product, 'products/5/large.webp', 5))

		command.downgrade(config, '0006')
		with engine.begin() as connection:
			connection.exec_driver_sql('INSERT INTO app.product_images (id, product_id, storage_path, position) VALUES (%s, %s, %s, %s)', (uuid4(), product, 'products/5/large.webp', 5))
			assert connection.exec_driver_sql('SELECT count(*) FROM app.product_images').scalar_one() == 5
	finally:
		with engine.begin() as connection:
			connection.exec_driver_sql('DELETE FROM app.product_images WHERE position > 4')
		command.upgrade(config, 'head')
		engine.dispose()


def test_four_image_limit_migration_refuses_legacy_fifth_image_without_deleting_it(shop, product):
	config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
	engine.dispose()

	try:
		command.downgrade(config, '0006')
		with engine.begin() as connection:
			for position in range(1, 6):
				connection.exec_driver_sql('INSERT INTO app.product_images (id, product_id, storage_path, position) VALUES (%s, %s, %s, %s)', (uuid4(), product, f'products/{position}/large.webp', position))

		with pytest.raises(RuntimeError, match='posição 4'):
			command.upgrade(config, 'head')

		with engine.connect() as connection:
			assert connection.exec_driver_sql('SELECT count(*) FROM app.product_images').scalar_one() == 5
			assert connection.exec_driver_sql('SELECT version_num FROM public.alembic_version').scalar_one() == '0006'
	finally:
		with engine.begin() as connection:
			connection.exec_driver_sql('DELETE FROM app.product_images WHERE position > 4')
		command.upgrade(config, 'head')
		engine.dispose()


def test_product_migration_preserves_stores_on_upgrade_and_downgrade():
	config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
	store_id, product_id, image_id = uuid4(), uuid4(), uuid4()
	engine.dispose()

	try:
		command.downgrade(config, '0004')

		with engine.begin() as connection:
			connection.exec_driver_sql('INSERT INTO app.stores (id, name, slug) VALUES (%s, %s, %s)', (store_id, 'Loja existente', 'loja-existente'))

		command.upgrade(config, 'head')

		with engine.begin() as connection:
			connection.exec_driver_sql('INSERT INTO app.products (id, store_id, name, price) VALUES (%s, %s, %s, %s)', (product_id, store_id, 'Camiseta', Decimal('149.90')))
			connection.exec_driver_sql('INSERT INTO app.product_sizes (product_id, size, available) VALUES (%s, %s, %s)', (product_id, 'M', False))
			connection.exec_driver_sql('INSERT INTO app.product_images (id, product_id, storage_path, position) VALUES (%s, %s, %s, %s)', (image_id, product_id, 'products/image.webp', 1))

		command.downgrade(config, '0004')

		with engine.connect() as connection:
			assert connection.exec_driver_sql('SELECT name FROM app.stores WHERE id = %s', (store_id,)).scalar_one() == 'Loja existente'

			for table in ['products', 'product_sizes', 'product_images']:
				assert connection.exec_driver_sql('SELECT to_regclass(%s)', (f'app.{table}',)).scalar() is None
	finally:
		command.upgrade(config, 'head')
		engine.dispose()


def test_variant_migration_preserves_existing_references_and_downgrade_selects_largest_file():
	config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
	store_id, logo_id, cover_id = uuid4(), uuid4(), uuid4()
	engine.dispose()

	try:
		command.downgrade(config, '0003')

		with engine.begin() as connection:
			connection.exec_driver_sql('INSERT INTO app.stores (id, name, slug) VALUES (%s, %s, %s)', (store_id, 'Loja anterior', 'loja-anterior'))
			connection.exec_driver_sql('INSERT INTO app.store_images (id, store_id, type, storage_path, mime_type, width, height, size_bytes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', (logo_id, store_id, 'logo', 'stores/old/logo.png', 'image/png', 600, 400, 1000))
			connection.exec_driver_sql('INSERT INTO app.store_images (id, store_id, type, storage_path, mime_type, width, height, size_bytes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', (cover_id, store_id, 'cover', 'stores/old/cover.jpg', 'image/jpeg', 2000, 1200, 5000))

		command.upgrade(config, 'head')

		with engine.begin() as connection:
			rows = connection.exec_driver_sql('SELECT store_image_id, variant, storage_path, mime_type, width, height, size_bytes FROM app.store_image_variants').all()
			assert set(rows) == {(logo_id, 'medium', 'stores/old/logo.png', 'image/png', 600, 400, 1000), (cover_id, 'large', 'stores/old/cover.jpg', 'image/jpeg', 2000, 1200, 5000)}
			connection.exec_driver_sql("UPDATE app.store_image_variants SET storage_path = 'stores/new/medium.webp', mime_type = 'image/webp', width = 512, height = 256 WHERE store_image_id = %s", (logo_id,))
			connection.exec_driver_sql('INSERT INTO app.store_image_variants (store_image_id, variant, storage_path, mime_type, width, height, size_bytes) VALUES (%s, %s, %s, %s, %s, %s, %s)', (logo_id, 'small', 'stores/new/small.webp', 'image/webp', 256, 128, 500))

		command.downgrade(config, '0003')

		with engine.connect() as connection:
			logo = connection.exec_driver_sql('SELECT storage_path, mime_type, width, height FROM app.store_images WHERE id = %s', (logo_id,)).one()
			assert tuple(logo) == ('stores/new/medium.webp', 'image/webp', 512, 256)
	finally:
		# Deixa o banco de testes na versão atual, mesmo se uma verificação falhar.
		command.upgrade(config, 'head')
		engine.dispose()

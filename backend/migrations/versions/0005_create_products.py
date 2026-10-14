"""Cria produtos, tamanhos e referências de imagens."""

from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table('products', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('store_id', sa.Uuid(), nullable=False), sa.Column('name', sa.String(120), nullable=False), sa.Column('price', sa.Numeric(10, 2), nullable=False), sa.Column('description', sa.Text(), nullable=True), sa.PrimaryKeyConstraint('id'), sa.ForeignKeyConstraint(['store_id'], ['app.stores.id'], name='fk_products_store_id', ondelete='CASCADE'), sa.CheckConstraint("btrim(name) <> ''", name='ck_products_name'), sa.CheckConstraint("price >= 0 AND price <> 'NaN'::numeric", name='ck_products_price'), schema='app')
	op.create_index('ix_products_store_id', 'products', ['store_id'], schema='app')

	op.create_table('product_sizes', sa.Column('product_id', sa.Uuid(), nullable=False), sa.Column('size', sa.String(20), nullable=False), sa.Column('available', sa.Boolean(), nullable=False), sa.PrimaryKeyConstraint('product_id', 'size'), sa.ForeignKeyConstraint(['product_id'], ['app.products.id'], name='fk_product_sizes_product_id', ondelete='CASCADE'), sa.CheckConstraint("btrim(size) <> ''", name='ck_product_sizes_size'), schema='app')

	op.create_table('product_images', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('product_id', sa.Uuid(), nullable=False), sa.Column('storage_path', sa.String(255), nullable=False), sa.Column('position', sa.Integer(), nullable=False), sa.PrimaryKeyConstraint('id'), sa.ForeignKeyConstraint(['product_id'], ['app.products.id'], name='fk_product_images_product_id', ondelete='CASCADE'), sa.UniqueConstraint('product_id', 'position', name='uq_product_images_product_position'), sa.CheckConstraint('position BETWEEN 1 AND 5', name='ck_product_images_position'), sa.CheckConstraint("btrim(storage_path) <> ''", name='ck_product_images_storage_path'), schema='app')


def downgrade() -> None:
	op.drop_table('product_images', schema='app')
	op.drop_table('product_sizes', schema='app')
	op.drop_table('products', schema='app')

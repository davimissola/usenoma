"""Cria referências e metadados das imagens de lojas."""

from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table('store_images', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('store_id', sa.Uuid(), nullable=False), sa.Column('type', sa.String(5), nullable=False), sa.Column('storage_path', sa.String(255), nullable=False), sa.Column('mime_type', sa.String(32), nullable=False), sa.Column('width', sa.Integer(), nullable=False), sa.Column('height', sa.Integer(), nullable=False), sa.Column('size_bytes', sa.Integer(), nullable=False), sa.PrimaryKeyConstraint('id'), sa.ForeignKeyConstraint(['store_id'], ['app.stores.id'], name='fk_store_images_store_id', ondelete='CASCADE'), sa.UniqueConstraint('store_id', 'type', name='uq_store_images_store_type'), sa.CheckConstraint("type IN ('logo', 'cover')", name='ck_store_images_type'), sa.CheckConstraint("btrim(storage_path) <> ''", name='ck_store_images_storage_path'), sa.CheckConstraint("mime_type IN ('image/jpeg', 'image/png', 'image/webp')", name='ck_store_images_mime_type'), sa.CheckConstraint('width > 0 AND height > 0 AND size_bytes > 0', name='ck_store_images_metadata'), schema='app')


def downgrade() -> None:
	op.drop_table('store_images', schema='app')

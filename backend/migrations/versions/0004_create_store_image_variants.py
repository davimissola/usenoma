"""Separa a imagem lógica de seus arquivos e preserva referências existentes."""

from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table('store_image_variants', sa.Column('store_image_id', sa.Uuid(), nullable=False), sa.Column('variant', sa.String(6), nullable=False), sa.Column('storage_path', sa.String(255), nullable=False), sa.Column('mime_type', sa.String(32), nullable=False), sa.Column('width', sa.Integer(), nullable=False), sa.Column('height', sa.Integer(), nullable=False), sa.Column('size_bytes', sa.Integer(), nullable=False), sa.PrimaryKeyConstraint('store_image_id', 'variant'), sa.ForeignKeyConstraint(['store_image_id'], ['app.store_images.id'], name='fk_store_image_variants_image_id', ondelete='CASCADE'), sa.CheckConstraint("variant IN ('small', 'medium', 'large')", name='ck_store_image_variants_variant'), sa.CheckConstraint("btrim(storage_path) <> ''", name='ck_store_image_variants_storage_path'), sa.CheckConstraint("mime_type IN ('image/jpeg', 'image/png', 'image/webp')", name='ck_store_image_variants_mime_type'), sa.CheckConstraint('width > 0 AND height > 0 AND size_bytes > 0', name='ck_store_image_variants_metadata'), schema='app')
	# Migration altera referências, não baixa ou processa arquivos no Storage.
	op.execute("INSERT INTO app.store_image_variants (store_image_id, variant, storage_path, mime_type, width, height, size_bytes) SELECT id, CASE WHEN type = 'logo' THEN 'medium' ELSE 'large' END, storage_path, mime_type, width, height, size_bytes FROM app.store_images")
	op.drop_constraint('ck_store_images_storage_path', 'store_images', schema='app', type_='check')
	op.drop_constraint('ck_store_images_mime_type', 'store_images', schema='app', type_='check')
	op.drop_constraint('ck_store_images_metadata', 'store_images', schema='app', type_='check')

	for column in ['storage_path', 'mime_type', 'width', 'height', 'size_bytes']:
		op.drop_column('store_images', column, schema='app')


def downgrade() -> None:
	op.add_column('store_images', sa.Column('storage_path', sa.String(255), nullable=True), schema='app')
	op.add_column('store_images', sa.Column('mime_type', sa.String(32), nullable=True), schema='app')
	op.add_column('store_images', sa.Column('width', sa.Integer(), nullable=True), schema='app')
	op.add_column('store_images', sa.Column('height', sa.Integer(), nullable=True), schema='app')
	op.add_column('store_images', sa.Column('size_bytes', sa.Integer(), nullable=True), schema='app')
	# O formato antigo comporta um arquivo: recupera a maior variante, sem alterar o Storage.
	op.execute("UPDATE app.store_images AS image SET storage_path = source.storage_path, mime_type = source.mime_type, width = source.width, height = source.height, size_bytes = source.size_bytes FROM (SELECT DISTINCT ON (store_image_id) store_image_id, storage_path, mime_type, width, height, size_bytes FROM app.store_image_variants ORDER BY store_image_id, width::bigint * height DESC, CASE variant WHEN 'large' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END DESC) AS source WHERE image.id = source.store_image_id")

	for column in ['storage_path', 'mime_type', 'width', 'height', 'size_bytes']:
		op.alter_column('store_images', column, nullable=False, schema='app')

	op.create_check_constraint('ck_store_images_storage_path', 'store_images', "btrim(storage_path) <> ''", schema='app')
	op.create_check_constraint('ck_store_images_mime_type', 'store_images', "mime_type IN ('image/jpeg', 'image/png', 'image/webp')", schema='app')
	op.create_check_constraint('ck_store_images_metadata', 'store_images', 'width > 0 AND height > 0 AND size_bytes > 0', schema='app')
	op.drop_table('store_image_variants', schema='app')

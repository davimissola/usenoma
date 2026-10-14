"""Permite reordenar imagens sem violar a unicidade durante a troca de posições."""

from alembic import op


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.drop_constraint('uq_product_images_product_position', 'product_images', schema='app', type_='unique')
	op.create_unique_constraint('uq_product_images_product_position', 'product_images', ['product_id', 'position'], schema='app', deferrable=True, initially='IMMEDIATE')


def downgrade() -> None:
	op.drop_constraint('uq_product_images_product_position', 'product_images', schema='app', type_='unique')
	op.create_unique_constraint('uq_product_images_product_position', 'product_images', ['product_id', 'position'], schema='app')

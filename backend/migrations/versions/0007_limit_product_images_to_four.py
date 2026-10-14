"""Limita cada produto a quatro posições de imagem."""

from alembic import op
import sqlalchemy as sa


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
	# Interrompe sem apagar dados se o limite antigo ainda estiver sendo utilizado.
	if op.get_bind().execute(sa.text('SELECT 1 FROM app.product_images WHERE position > 4 LIMIT 1')).first():
		raise RuntimeError('Existem imagens acima da posição 4. Remova a imagem excedente e reordene pelo backend antes de aplicar esta migration.')

	op.drop_constraint('ck_product_images_position', 'product_images', schema='app', type_='check')
	op.create_check_constraint('ck_product_images_position', 'product_images', 'position BETWEEN 1 AND 4', schema='app')


def downgrade() -> None:
	op.drop_constraint('ck_product_images_position', 'product_images', schema='app', type_='check')
	op.create_check_constraint('ck_product_images_position', 'product_images', 'position BETWEEN 1 AND 5', schema='app')

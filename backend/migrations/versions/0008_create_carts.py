"""Cria carrinhos e itens persistidos por usuário."""

from alembic import op
import sqlalchemy as sa


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table('carts', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('user_id', sa.Uuid(), nullable=False), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.PrimaryKeyConstraint('id'), sa.ForeignKeyConstraint(['user_id'], ['app.users.id'], name='fk_carts_user_id', ondelete='CASCADE'), sa.UniqueConstraint('user_id', name='uq_carts_user_id'), schema='app')
	op.create_table('cart_items', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('cart_id', sa.Uuid(), nullable=False), sa.Column('product_id', sa.Uuid(), nullable=True), sa.Column('size', sa.String(20), nullable=False), sa.Column('quantity', sa.Integer(), nullable=False), sa.PrimaryKeyConstraint('id'), sa.ForeignKeyConstraint(['cart_id'], ['app.carts.id'], name='fk_cart_items_cart_id', ondelete='CASCADE'), sa.ForeignKeyConstraint(['product_id'], ['app.products.id'], name='fk_cart_items_product_id', ondelete='SET NULL'), sa.UniqueConstraint('cart_id', 'product_id', 'size', name='uq_cart_items_cart_product_size'), sa.CheckConstraint('quantity >= 1', name='ck_cart_items_quantity'), sa.CheckConstraint("btrim(size) <> ''", name='ck_cart_items_size'), schema='app')
	op.create_index('ix_cart_items_product_id', 'cart_items', ['product_id'], schema='app')


def downgrade() -> None:
	op.drop_table('cart_items', schema='app')
	op.drop_table('carts', schema='app')

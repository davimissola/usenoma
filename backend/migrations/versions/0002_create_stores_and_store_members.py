"""Cria lojas e seus responsáveis."""

from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table('stores', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('name', sa.String(120), nullable=False), sa.Column('slug', sa.String(120), nullable=False), sa.Column('description', sa.Text(), nullable=True), sa.PrimaryKeyConstraint('id'), sa.UniqueConstraint('slug', name='uq_stores_slug'), sa.CheckConstraint("btrim(name) <> ''", name='ck_stores_name'), sa.CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name='ck_stores_slug'), schema='app')

	op.create_table('store_members', sa.Column('store_id', sa.Uuid(), nullable=False), sa.Column('user_id', sa.Uuid(), nullable=False), sa.Column('role', sa.String(7), nullable=False), sa.PrimaryKeyConstraint('store_id', 'user_id'), sa.ForeignKeyConstraint(['store_id'], ['app.stores.id'], name='fk_store_members_store_id', ondelete='CASCADE'), sa.ForeignKeyConstraint(['user_id'], ['app.users.id'], name='fk_store_members_user_id', ondelete='RESTRICT'), sa.CheckConstraint("role IN ('owner', 'manager')", name='ck_store_members_role'), schema='app')
	op.create_index('ix_store_members_user_id', 'store_members', ['user_id'], schema='app')


def downgrade() -> None:
	op.drop_table('store_members', schema='app')
	op.drop_table('stores', schema='app')

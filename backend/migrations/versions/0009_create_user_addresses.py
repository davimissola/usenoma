"""Cria endereços do usuário e garante no máximo um padrão por conta."""

from alembic import op
import sqlalchemy as sa


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table('user_addresses', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('user_id', sa.Uuid(), nullable=False), sa.Column('recipient_name', sa.String(120), nullable=False), sa.Column('postal_code', sa.String(8), nullable=False), sa.Column('street', sa.String(200), nullable=False), sa.Column('number', sa.String(20), nullable=False), sa.Column('complement', sa.String(120), nullable=True), sa.Column('neighborhood', sa.String(120), nullable=False), sa.Column('city', sa.String(120), nullable=False), sa.Column('state', sa.String(2), nullable=False), sa.Column('phone', sa.String(11), nullable=False), sa.Column('is_default', sa.Boolean(), server_default=sa.false(), nullable=False), sa.PrimaryKeyConstraint('id'), sa.ForeignKeyConstraint(['user_id'], ['app.users.id'], name='fk_user_addresses_user_id', ondelete='CASCADE'), sa.CheckConstraint("btrim(recipient_name) <> ''", name='ck_user_addresses_recipient_name'), sa.CheckConstraint("postal_code ~ '^[0-9]{8}$'", name='ck_user_addresses_postal_code'), sa.CheckConstraint("btrim(street) <> ''", name='ck_user_addresses_street'), sa.CheckConstraint("btrim(number) <> ''", name='ck_user_addresses_number'), sa.CheckConstraint("complement IS NULL OR btrim(complement) <> ''", name='ck_user_addresses_complement'), sa.CheckConstraint("btrim(neighborhood) <> ''", name='ck_user_addresses_neighborhood'), sa.CheckConstraint("btrim(city) <> ''", name='ck_user_addresses_city'), sa.CheckConstraint("state IN ('AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO')", name='ck_user_addresses_state'), sa.CheckConstraint("phone ~ '^[0-9]{10,11}$'", name='ck_user_addresses_phone'), schema='app')
	op.create_index('ix_user_addresses_user_id', 'user_addresses', ['user_id'], schema='app')
	op.create_index('uq_user_addresses_default', 'user_addresses', ['user_id'], unique=True, postgresql_where=sa.text('is_default'), schema='app')


def downgrade() -> None:
	op.drop_table('user_addresses', schema='app')

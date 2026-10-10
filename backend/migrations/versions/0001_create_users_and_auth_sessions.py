"""Cria usuários e sessões de autenticação."""

from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.execute('CREATE SCHEMA IF NOT EXISTS app')

	op.create_table('users', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('username', sa.String(30), nullable=False), sa.Column('email', sa.String(254), nullable=False), sa.Column('password_hash', sa.String(255), nullable=False), sa.PrimaryKeyConstraint('id'), sa.CheckConstraint("username ~ '^[A-Za-z0-9_.]{3,30}$'", name='ck_users_username'), schema='app')
	op.create_index('uq_users_username', 'users', [sa.text('lower(username)')], unique=True, schema='app')
	op.create_index('uq_users_email', 'users', [sa.text('lower(email)')], unique=True, schema='app')

	op.create_table('auth_sessions', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('user_id', sa.Uuid(), nullable=False), sa.Column('token_hash', sa.String(64), nullable=False), sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False), sa.Column('revoked', sa.Boolean(), server_default=sa.false(), nullable=False), sa.PrimaryKeyConstraint('id'), sa.ForeignKeyConstraint(['user_id'], ['app.users.id'], ondelete='CASCADE'), sa.UniqueConstraint('token_hash'), sa.CheckConstraint('char_length(token_hash) = 64', name='ck_auth_sessions_token_hash'), schema='app')
	op.create_index('ix_auth_sessions_user_id', 'auth_sessions', ['user_id'], schema='app')


def downgrade() -> None:
	op.drop_table('auth_sessions', schema='app')
	op.drop_table('users', schema='app')

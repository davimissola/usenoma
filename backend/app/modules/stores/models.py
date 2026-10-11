from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Store(Base):
	__tablename__ = 'stores'

	id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	name: Mapped[str] = mapped_column(String(120), nullable=False)
	slug: Mapped[str] = mapped_column(String(120), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	__table_args__ = (
		UniqueConstraint('slug', name='uq_stores_slug'),
		CheckConstraint("btrim(name) <> ''", name='ck_stores_name'),
		CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name='ck_stores_slug'),
	)


class StoreMember(Base):
	__tablename__ = 'store_members'

	# A chave composta identifica o vínculo e impede repetir um usuário na mesma loja.
	store_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('app.stores.id', name='fk_store_members_store_id', ondelete='CASCADE'), primary_key=True)
	# A conta só pode ser excluída depois de remover ou reorganizar seus vínculos.
	user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('app.users.id', name='fk_store_members_user_id', ondelete='RESTRICT'), primary_key=True)
	role: Mapped[str] = mapped_column(String(7), nullable=False)

	__table_args__ = (
		CheckConstraint("role IN ('owner', 'manager')", name='ck_store_members_role'),
		# A PK já atende buscas por loja; este índice atende buscas das lojas do usuário.
		Index('ix_store_members_user_id', 'user_id'),
	)

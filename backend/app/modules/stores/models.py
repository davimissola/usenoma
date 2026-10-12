from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
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


class StoreImage(Base):
	__tablename__ = 'store_images'

	id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	store_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('app.stores.id', name='fk_store_images_store_id', ondelete='CASCADE'), nullable=False)
	type: Mapped[str] = mapped_column(String(5), nullable=False)

	__table_args__ = (
		# A imagem lógica continua sendo única: uma logo e uma cover por loja.
		UniqueConstraint('store_id', 'type', name='uq_store_images_store_type'),
		CheckConstraint("type IN ('logo', 'cover')", name='ck_store_images_type'),
	)


class StoreImageVariant(Base):
	__tablename__ = 'store_image_variants'

	# A chave composta identifica cada tamanho sem criar outro id sem uso.
	store_image_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('app.store_images.id', name='fk_store_image_variants_image_id', ondelete='CASCADE'), primary_key=True)
	variant: Mapped[str] = mapped_column(String(6), primary_key=True)
	storage_path: Mapped[str] = mapped_column(String(255), nullable=False)
	mime_type: Mapped[str] = mapped_column(String(32), nullable=False)
	width: Mapped[int] = mapped_column(Integer, nullable=False)
	height: Mapped[int] = mapped_column(Integer, nullable=False)
	size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

	__table_args__ = (
		CheckConstraint("variant IN ('small', 'medium', 'large')", name='ck_store_image_variants_variant'),
		CheckConstraint("btrim(storage_path) <> ''", name='ck_store_image_variants_storage_path'),
		# JPEG/PNG preservam referências do 3A; novos uploads são sempre WebP.
		CheckConstraint("mime_type IN ('image/jpeg', 'image/png', 'image/webp')", name='ck_store_image_variants_mime_type'),
		CheckConstraint('width > 0 AND height > 0 AND size_bytes > 0', name='ck_store_image_variants_metadata'),
	)

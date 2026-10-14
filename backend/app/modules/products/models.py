from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
	__tablename__ = 'products'

	id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	store_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('app.stores.id', name='fk_products_store_id', ondelete='CASCADE'), nullable=False)
	name: Mapped[str] = mapped_column(String(120), nullable=False)
	# Numeric retorna Decimal; o preço é persistido com duas casas decimais.
	price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	__table_args__ = (
		CheckConstraint("btrim(name) <> ''", name='ck_products_name'),
		CheckConstraint("price >= 0 AND price <> 'NaN'::numeric", name='ck_products_price'),
		Index('ix_products_store_id', 'store_id'),
	)


class ProductSize(Base):
	__tablename__ = 'product_sizes'

	product_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('app.products.id', name='fk_product_sizes_product_id', ondelete='CASCADE'), primary_key=True)
	size: Mapped[str] = mapped_column(String(20), primary_key=True)
	available: Mapped[bool] = mapped_column(Boolean, nullable=False)

	__table_args__ = (
		CheckConstraint("btrim(size) <> ''", name='ck_product_sizes_size'),
	)


class ProductImage(Base):
	__tablename__ = 'product_images'

	id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	product_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('app.products.id', name='fk_product_images_product_id', ondelete='CASCADE'), nullable=False)
	storage_path: Mapped[str] = mapped_column(String(255), nullable=False)
	position: Mapped[int] = mapped_column(Integer, nullable=False)

	__table_args__ = (
		# Cinco posições únicas garantem o limite de imagens, inclusive em inserções concorrentes.
		UniqueConstraint('product_id', 'position', name='uq_product_images_product_position', deferrable=True, initially='IMMEDIATE'),
		CheckConstraint('position BETWEEN 1 AND 5', name='ck_product_images_position'),
		CheckConstraint("btrim(storage_path) <> ''", name='ck_product_images_storage_path'),
	)

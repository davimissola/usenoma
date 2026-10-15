from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Cart(Base):
	__tablename__ = 'carts'

	id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('app.users.id', name='fk_carts_user_id', ondelete='CASCADE'), nullable=False)
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

	__table_args__ = (UniqueConstraint('user_id', name='uq_carts_user_id'),)


class CartItem(Base):
	__tablename__ = 'cart_items'

	id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	cart_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('app.carts.id', name='fk_cart_items_cart_id', ondelete='CASCADE'), nullable=False)
	# Preserva o item quando o produto é excluído; a leitura informa sua indisponibilidade.
	product_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey('app.products.id', name='fk_cart_items_product_id', ondelete='SET NULL'), nullable=True)
	size: Mapped[str] = mapped_column(String(20), nullable=False)
	quantity: Mapped[int] = mapped_column(Integer, nullable=False)

	__table_args__ = (
		UniqueConstraint('cart_id', 'product_id', 'size', name='uq_cart_items_cart_product_size'),
		CheckConstraint('quantity >= 1', name='ck_cart_items_quantity'),
		CheckConstraint("btrim(size) <> ''", name='ck_cart_items_size'),
		Index('ix_cart_items_product_id', 'product_id'),
	)

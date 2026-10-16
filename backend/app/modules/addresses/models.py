from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Uuid, false, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserAddress(Base):
	__tablename__ = 'user_addresses'

	id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('app.users.id', name='fk_user_addresses_user_id', ondelete='CASCADE'), nullable=False)
	recipient_name: Mapped[str] = mapped_column(String(120), nullable=False)
	postal_code: Mapped[str] = mapped_column(String(8), nullable=False)
	street: Mapped[str] = mapped_column(String(200), nullable=False)
	number: Mapped[str] = mapped_column(String(20), nullable=False)
	complement: Mapped[str | None] = mapped_column(String(120), nullable=True)
	neighborhood: Mapped[str] = mapped_column(String(120), nullable=False)
	city: Mapped[str] = mapped_column(String(120), nullable=False)
	state: Mapped[str] = mapped_column(String(2), nullable=False)
	phone: Mapped[str] = mapped_column(String(11), nullable=False)
	is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())

	__table_args__ = (
		Index('ix_user_addresses_user_id', 'user_id'),
		# Só os endereços marcados participam deste índice único.
		Index('uq_user_addresses_default', 'user_id', unique=True, postgresql_where=text('is_default')),
		CheckConstraint("btrim(recipient_name) <> ''", name='ck_user_addresses_recipient_name'),
		CheckConstraint("postal_code ~ '^[0-9]{8}$'", name='ck_user_addresses_postal_code'),
		CheckConstraint("btrim(street) <> ''", name='ck_user_addresses_street'),
		CheckConstraint("btrim(number) <> ''", name='ck_user_addresses_number'),
		CheckConstraint("complement IS NULL OR btrim(complement) <> ''", name='ck_user_addresses_complement'),
		CheckConstraint("btrim(neighborhood) <> ''", name='ck_user_addresses_neighborhood'),
		CheckConstraint("btrim(city) <> ''", name='ck_user_addresses_city'),
		CheckConstraint("state IN ('AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO')", name='ck_user_addresses_state'),
		CheckConstraint("phone ~ '^[0-9]{10,11}$'", name='ck_user_addresses_phone'),
	)

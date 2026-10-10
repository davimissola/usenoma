from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
	__tablename__ = 'users'

	id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	username: Mapped[str] = mapped_column(String(30), nullable=False)
	email: Mapped[str] = mapped_column(String(254), nullable=False)
	password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

	__table_args__ = (
		Index('uq_users_username', func.lower(username), unique=True),
		Index('uq_users_email', func.lower(email), unique=True),
		CheckConstraint("username ~ '^[A-Za-z0-9_.]{3,30}$'", name='ck_users_username'),
	)

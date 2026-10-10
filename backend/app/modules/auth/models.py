from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuthSession(Base):
	__tablename__ = 'auth_sessions'
	__table_args__ = (CheckConstraint('char_length(token_hash) = 64', name='ck_auth_sessions_token_hash'), Index('ix_auth_sessions_user_id', 'user_id'))

	id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('app.users.id', ondelete='CASCADE'), nullable=False)
	token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
	expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.auth.models import AuthSession
from app.modules.auth.schemas import RegisterRequest
from app.modules.auth.security import DUMMY_PASSWORD_HASH, create_refresh_token, hash_password, hash_refresh_token, verify_password
from app.modules.users.models import User


def create_session(db: Session, user_id: UUID) -> tuple[str, datetime]:
	refresh_token = create_refresh_token()
	expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

	db.add(AuthSession(user_id=user_id, token_hash=hash_refresh_token(refresh_token), expires_at=expires_at))

	return refresh_token, expires_at


def register_user(db: Session, data: RegisterRequest) -> tuple[UUID, str, datetime]:
	user = User(username=data.username, email=str(data.email), password_hash=hash_password(data.password.get_secret_value()))

	try:
		db.add(user)
		db.flush()
		refresh_token, expires_at = create_session(db, user.id)
		db.commit()
	except IntegrityError as error:
		db.rollback()
		constraint = getattr(getattr(error.orig, 'diag', None), 'constraint_name', None)

		if constraint in {'uq_users_username', 'uq_users_email'}:
			raise HTTPException(status_code=409, detail='Nome de usuário ou email já cadastrado.') from error

		raise

	return user.id, refresh_token, expires_at


def login_user(db: Session, username: str, password: str) -> tuple[UUID, str, datetime]:
	user = db.scalar(select(User).where(func.lower(User.username) == username.strip().lower()))

	if user:
		hashed_password = user.password_hash
	else:
		hashed_password = DUMMY_PASSWORD_HASH

	valid_password = verify_password(password, hashed_password)

	if not user or not valid_password:
		raise HTTPException(status_code=401, detail='Nome de usuário ou senha incorretos.', headers={'WWW-Authenticate': 'Bearer'})

	refresh_token, expires_at = create_session(db, user.id)
	db.commit()

	return user.id, refresh_token, expires_at


def refresh_session(db: Session, refresh_token: str) -> tuple[UUID, str, datetime]:
	session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_refresh_token(refresh_token)).with_for_update())

	if not session or session.revoked or session.expires_at <= datetime.now(timezone.utc):
		db.rollback()
		raise HTTPException(status_code=401, detail='Sessão inválida ou expirada.')

	new_refresh_token = create_refresh_token()
	session.token_hash = hash_refresh_token(new_refresh_token)
	db.commit()

	return session.user_id, new_refresh_token, session.expires_at


def logout_session(db: Session, refresh_token: str | None) -> None:
	if not refresh_token:
		return

	db.execute(update(AuthSession).where(AuthSession.token_hash == hash_refresh_token(refresh_token)).values(revoked=True))
	db.commit()

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import settings


ALGORITHM = 'HS256'
password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash(token_urlsafe(32))


def hash_password(password: str) -> str:
	return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
	return password_hash.verify(password, hashed_password)


def create_access_token(user_id: UUID) -> str:
	expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
	payload = {'sub': str(user_id), 'exp': expires_at}

	return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> UUID:
	payload = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=[ALGORITHM], options={'require': ['sub', 'exp']})

	return UUID(payload['sub'])


def create_refresh_token() -> str:
	return token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
	return sha256(token.encode()).hexdigest()

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.database import DbSession
from app.modules.auth.dependencies import verify_request_origin
from app.modules.auth.schemas import RegisterRequest, TokenResponse
from app.modules.auth.security import create_access_token
from app.modules.auth.service import login_user, logout_session, refresh_session, register_user


router = APIRouter(prefix='/auth', tags=['Auth'], dependencies=[Depends(verify_request_origin)])


# coloca o refresh token no cookie HttpOnly
def set_refresh_cookie(response: Response, refresh_token: str, expires_at: datetime) -> None:
	expires_at = expires_at.astimezone(timezone.utc)
	max_age = max(0, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
	response.set_cookie(key='refresh_token', value=refresh_token, max_age=max_age, expires=expires_at, path='/', secure=settings.cookie_secure, httponly=True, samesite='lax')
	response.headers['Cache-Control'] = 'no-store'


# retorna o token de 30 minutos -> access_token
@router.post('/register', response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, response: Response, db: DbSession) -> TokenResponse:
	user_id, refresh_token, expires_at = register_user(db, data)
	set_refresh_cookie(response, refresh_token, expires_at)

	return TokenResponse(access_token=create_access_token(user_id))


@router.post('/login', response_model=TokenResponse)
def login(response: Response, data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> TokenResponse:
	user_id, refresh_token, expires_at = login_user(db, data.username, data.password)
	set_refresh_cookie(response, refresh_token, expires_at)

	return TokenResponse(access_token=create_access_token(user_id))


# cria o novo access_token ai
@router.post('/refresh', response_model=TokenResponse)
def refresh(response: Response, db: DbSession, refresh_token: Annotated[str | None, Cookie()] = None) -> TokenResponse:
	if not refresh_token:
		raise HTTPException(status_code=401, detail='Sessão não encontrada.')

	user_id, new_refresh_token, expires_at = refresh_session(db, refresh_token)
	set_refresh_cookie(response, new_refresh_token, expires_at)

	return TokenResponse(access_token=create_access_token(user_id))


@router.post('/logout', status_code=204)
def logout(response: Response, db: DbSession, refresh_token: Annotated[str | None, Cookie()] = None) -> Response:
	logout_session(db, refresh_token)
	response.delete_cookie(key='refresh_token', path='/', secure=settings.cookie_secure, httponly=True, samesite='lax')
	response.headers['Cache-Control'] = 'no-store'
	response.status_code = 204

	return response

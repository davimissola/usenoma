from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError

from app.core.config import settings
from app.modules.auth.security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login')


def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> UUID:
	try:
		return decode_access_token(token)
	except (InvalidTokenError, ValueError, TypeError) as error:
		raise HTTPException(status_code=401, detail='Token inválido ou expirado.', headers={'WWW-Authenticate': 'Bearer'}) from error


def verify_request_origin(request: Request) -> None:
	base_url = urlsplit(str(request.base_url))
	api_origin = f'{base_url.scheme}://{base_url.netloc}'
	origin = request.headers.get('origin')

	if not origin:
		referer = urlsplit(request.headers.get('referer', ''))
		origin = f'{referer.scheme}://{referer.netloc}' if referer.scheme and referer.netloc else None

	if origin not in {settings.frontend_url, api_origin}:
		raise HTTPException(status_code=403, detail='Origem da requisição não permitida.')


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]

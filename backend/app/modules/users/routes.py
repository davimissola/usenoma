from fastapi import APIRouter, HTTPException

from app.core.database import DbSession
from app.modules.auth.dependencies import CurrentUserId
from app.modules.users.models import User
from app.modules.users.schemas import UserResponse


router = APIRouter(prefix='/users', tags=['Users'])


@router.get('/me', response_model=UserResponse)
def get_me(user_id: CurrentUserId, db: DbSession) -> User:
	user = db.get(User, user_id)

	if not user:
		raise HTTPException(status_code=401, detail='Usuário não encontrado.', headers={'WWW-Authenticate': 'Bearer'})

	return user

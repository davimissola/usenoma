from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.database import DbSession
from app.modules.auth.dependencies import CurrentUserId
from app.modules.stores.models import Store, StoreMember
from app.modules.users.models import User
from app.modules.users.schemas import UserResponse, UserStoreResponse


router = APIRouter(prefix='/users', tags=['Users'])


@router.get('/me', response_model=UserResponse)
def get_me(user_id: CurrentUserId, db: DbSession) -> UserResponse:
	user = db.get(User, user_id)

	if not user:
		raise HTTPException(status_code=401, detail='Usuário não encontrado.', headers={'WWW-Authenticate': 'Bearer'})

	# O vínculo basta: owner e manager entram na mesma lista, sem expor o cargo.
	stores = db.execute(select(Store.id, Store.name, Store.slug).join(StoreMember, StoreMember.store_id == Store.id).where(StoreMember.user_id == user_id).order_by(Store.name, Store.id)).all()

	return UserResponse(id=user.id, username=user.username, email=user.email, stores=[UserStoreResponse.model_validate(store) for store in stores])

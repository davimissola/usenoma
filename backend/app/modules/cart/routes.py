from uuid import UUID

from fastapi import APIRouter, Response

from app.core.database import DbSession
from app.modules.auth.dependencies import CurrentUserId
from app.modules.cart import service
from app.modules.cart.schemas import CartItemCreate, CartItemUpdate, CartResponse


router = APIRouter(prefix='/cart', tags=['Cart'])


@router.get('', response_model=CartResponse)
def get_cart(user_id: CurrentUserId, db: DbSession, response: Response) -> CartResponse:
	response.headers['Cache-Control'] = 'no-store'
	return service.get_cart(db, user_id)


@router.post('/items', response_model=CartResponse)
def add_item(data: CartItemCreate, user_id: CurrentUserId, db: DbSession) -> CartResponse:
	return service.add_item(db, user_id, data)


@router.patch('/items/{item_id}', response_model=CartResponse)
def update_item(item_id: UUID, data: CartItemUpdate, user_id: CurrentUserId, db: DbSession) -> CartResponse:
	return service.update_item(db, user_id, item_id, data)


@router.delete('/items/{item_id}', status_code=204)
def remove_item(item_id: UUID, user_id: CurrentUserId, db: DbSession) -> None:
	service.remove_item(db, user_id, item_id)


@router.delete('', status_code=204)
def clear_cart(user_id: CurrentUserId, db: DbSession) -> None:
	service.clear_cart(db, user_id)

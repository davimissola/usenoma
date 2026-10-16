from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.core.database import DbSession
from app.modules.addresses import service
from app.modules.addresses.models import UserAddress
from app.modules.addresses.schemas import UserAddressCreate, UserAddressResponse, UserAddressUpdate
from app.modules.auth.dependencies import CurrentUserId


router = APIRouter(prefix='/users/me/addresses', tags=['Addresses'])


@router.post('', response_model=UserAddressResponse, status_code=201)
def create_address(data: UserAddressCreate, user_id: CurrentUserId, db: DbSession, response: Response) -> UserAddress:
	response.headers['Cache-Control'] = 'no-store'
	return service.create_address(db, user_id, data)


@router.get('', response_model=list[UserAddressResponse])
def list_addresses(user_id: CurrentUserId, db: DbSession, response: Response, offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[UserAddress]:
	response.headers['Cache-Control'] = 'no-store'
	return service.list_addresses(db, user_id, offset, limit)


@router.get('/{address_id}', response_model=UserAddressResponse)
def get_address(address_id: UUID, user_id: CurrentUserId, db: DbSession, response: Response) -> UserAddress:
	response.headers['Cache-Control'] = 'no-store'
	return service.get_address(db, user_id, address_id)


@router.patch('/{address_id}', response_model=UserAddressResponse)
def update_address(address_id: UUID, data: UserAddressUpdate, user_id: CurrentUserId, db: DbSession, response: Response) -> UserAddress:
	response.headers['Cache-Control'] = 'no-store'
	return service.update_address(db, user_id, address_id, data)


@router.delete('/{address_id}', status_code=204)
def delete_address(address_id: UUID, user_id: CurrentUserId, db: DbSession) -> None:
	service.delete_address(db, user_id, address_id)

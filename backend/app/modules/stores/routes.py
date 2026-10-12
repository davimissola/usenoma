from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile

from app.core.database import DbSession
from app.modules.auth.dependencies import CurrentUserId
from app.modules.stores import image_service, service
from app.modules.stores.models import Store
from app.modules.stores.schemas import StoreImageResponse, StoreImageType, StoreMemberCreate, StoreMemberResponse, StoreMemberUpdate, StorePublicResponse, StoreResponse, StoreUpdate


router = APIRouter(prefix='/stores', tags=['Stores'])




@router.get('/slug/{slug}', response_model=StorePublicResponse)
def get_by_slug(slug: str, db: DbSession) -> StorePublicResponse:
	return service.get_public_store_by_slug(db, slug)


@router.get('/{store_id}', response_model=StoreResponse)
def get_by_id(store_id: UUID, db: DbSession) -> Store:
	return service.get_store(db, store_id)


@router.patch('/{store_id}', response_model=StoreResponse)
def update(store_id: UUID, data: StoreUpdate, user_id: CurrentUserId, db: DbSession) -> Store:
	return service.update_store(db, store_id, user_id, data)


@router.get('/{store_id}/members', response_model=list[StoreMemberResponse])
def list_members(store_id: UUID, user_id: CurrentUserId, db: DbSession, offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[StoreMemberResponse]:
	return service.list_store_members(db, store_id, user_id, offset, limit)


@router.post('/{store_id}/members', response_model=StoreMemberResponse, status_code=201)
def add_member(store_id: UUID, data: StoreMemberCreate, user_id: CurrentUserId, db: DbSession) -> StoreMemberResponse:
	return service.add_store_member(db, store_id, user_id, data)


@router.patch('/{store_id}/members/{member_user_id}', response_model=StoreMemberResponse)
def update_member(store_id: UUID, member_user_id: UUID, data: StoreMemberUpdate, user_id: CurrentUserId, db: DbSession) -> StoreMemberResponse:
	return service.update_store_member(db, store_id, user_id, member_user_id, data)


@router.delete('/{store_id}/members/{member_user_id}', status_code=204)
def remove_member(store_id: UUID, member_user_id: UUID, user_id: CurrentUserId, db: DbSession) -> None:
	service.remove_store_member(db, store_id, user_id, member_user_id)


@router.put('/{store_id}/images/{image_type}', response_model=StoreImageResponse)
def upload_image(store_id: UUID, image_type: StoreImageType, file: Annotated[UploadFile, File()], user_id: CurrentUserId, db: DbSession) -> StoreImageResponse:
	# O service reutiliza a autorização da loja e retorna só as variantes prontas para uso.
	return image_service.upload_image(db, store_id, user_id, image_type, file)


@router.delete('/{store_id}/images/{image_type}', status_code=204)
def remove_image(store_id: UUID, image_type: StoreImageType, user_id: CurrentUserId, db: DbSession) -> None:
	image_service.remove_image(db, store_id, user_id, image_type)

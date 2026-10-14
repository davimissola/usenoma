from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile

from app.core.database import DbSession
from app.modules.auth.dependencies import CurrentUserId
from app.modules.products import image_service, service
from app.modules.products.models import ProductSize
from app.modules.products.schemas import ProductCreate, ProductImageOrder, ProductImageResponse, ProductResponse, ProductSizeCreate, ProductSizeName, ProductSizeResponse, ProductSizeUpdate, ProductUpdate


router = APIRouter(tags=['Products'])


@router.get('/stores/{store_id}/products', response_model=list[ProductResponse])
def list_products(store_id: UUID, db: DbSession, offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[ProductResponse]:
	return service.list_products(db, store_id, offset, limit)


@router.get('/products/{product_id}', response_model=ProductResponse)
def get_product(product_id: UUID, db: DbSession) -> ProductResponse:
	return service.get_product(db, product_id)


@router.post('/stores/{store_id}/products', response_model=ProductResponse, status_code=201)
def create_product(store_id: UUID, data: ProductCreate, user_id: CurrentUserId, db: DbSession) -> ProductResponse:
	return service.create_product(db, store_id, user_id, data)


@router.patch('/stores/{store_id}/products/{product_id}', response_model=ProductResponse)
def update_product(store_id: UUID, product_id: UUID, data: ProductUpdate, user_id: CurrentUserId, db: DbSession) -> ProductResponse:
	return service.update_product(db, store_id, product_id, user_id, data)


@router.delete('/stores/{store_id}/products/{product_id}', status_code=204)
def delete_product(store_id: UUID, product_id: UUID, user_id: CurrentUserId, db: DbSession) -> None:
	service.delete_product(db, store_id, product_id, user_id)


@router.post('/stores/{store_id}/products/{product_id}/sizes', response_model=ProductSizeResponse, status_code=201)
def add_size(store_id: UUID, product_id: UUID, data: ProductSizeCreate, user_id: CurrentUserId, db: DbSession) -> ProductSize:
	return service.add_size(db, store_id, product_id, user_id, data)


@router.patch('/stores/{store_id}/products/{product_id}/sizes/{size:path}', response_model=ProductSizeResponse)
def update_size(store_id: UUID, product_id: UUID, size: ProductSizeName, data: ProductSizeUpdate, user_id: CurrentUserId, db: DbSession) -> ProductSize:
	return service.update_size(db, store_id, product_id, user_id, size, data)


@router.delete('/stores/{store_id}/products/{product_id}/sizes/{size:path}', status_code=204)
def remove_size(store_id: UUID, product_id: UUID, size: ProductSizeName, user_id: CurrentUserId, db: DbSession) -> None:
	service.remove_size(db, store_id, product_id, user_id, size)


@router.post('/stores/{store_id}/products/{product_id}/images', response_model=ProductImageResponse, status_code=201)
def add_image(store_id: UUID, product_id: UUID, file: Annotated[UploadFile, File()], user_id: CurrentUserId, db: DbSession) -> ProductImageResponse:
	return image_service.upload_image(db, store_id, product_id, user_id, file)


@router.patch('/stores/{store_id}/products/{product_id}/images/order', response_model=list[ProductImageResponse])
def reorder_images(store_id: UUID, product_id: UUID, data: ProductImageOrder, user_id: CurrentUserId, db: DbSession) -> list[ProductImageResponse]:
	return image_service.reorder_images(db, store_id, product_id, user_id, data)


@router.put('/stores/{store_id}/products/{product_id}/images/{image_id}', response_model=ProductImageResponse)
def replace_image(store_id: UUID, product_id: UUID, image_id: UUID, file: Annotated[UploadFile, File()], user_id: CurrentUserId, db: DbSession) -> ProductImageResponse:
	return image_service.upload_image(db, store_id, product_id, user_id, file, image_id)


@router.delete('/stores/{store_id}/products/{product_id}/images/{image_id}', status_code=204)
def remove_image(store_id: UUID, product_id: UUID, image_id: UUID, user_id: CurrentUserId, db: DbSession) -> None:
	image_service.remove_image(db, store_id, product_id, user_id, image_id)

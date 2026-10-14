import logging
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.products import storage
from app.modules.products.image_processing import process_image, validate_image
from app.modules.products.models import ProductImage
from app.modules.products.schemas import ProductImageOrder, ProductImageResponse
from app.modules.products.service import build_image_response, lock_product, require_product_member


logger = logging.getLogger(__name__)


def get_image(db: Session, product_id: UUID, image_id: UUID) -> ProductImage:
	image = db.scalar(select(ProductImage).where(ProductImage.id == image_id, ProductImage.product_id == product_id))

	if not image:
		raise HTTPException(status_code=404, detail='Imagem não encontrada neste produto.')

	return image


def get_images(db: Session, product_id: UUID) -> list[ProductImage]:
	return list(db.scalars(select(ProductImage).where(ProductImage.product_id == product_id).order_by(ProductImage.position)).all())


def set_positions(db: Session, images: list[ProductImage]) -> None:
	# A unicidade é conferida no commit, permitindo trocar 1 e 2 sem posições temporárias.
	db.execute(text('SET CONSTRAINTS app.uq_product_images_product_position DEFERRED'))

	for position, image in enumerate(images, 1):
		image.position = position


def upload_image(db: Session, store_id: UUID, product_id: UUID, user_id: UUID, file: UploadFile, image_id: UUID | None = None) -> ProductImageResponse:
	require_product_member(db, store_id, product_id, user_id)

	if image_id is None:
		if len(get_images(db, product_id)) >= 5:
			raise HTTPException(status_code=409, detail='O produto pode ter no máximo cinco imagens.')
	else:
		get_image(db, product_id, image_id)

	# Nenhuma transação ou lock permanece durante processamento e chamadas ao Storage.
	db.rollback()
	processed = process_image(validate_image(file))
	folder = f'stores/{store_id}/products/{product_id}/{uuid4()}'
	new_path = f'{folder}/large.webp'
	paths = storage.image_paths(new_path)
	new_paths = []

	try:
		for variant, data in processed.items():
			new_paths.append(paths[variant])
			storage.upload_image(paths[variant], data, 'image/webp')
	except HTTPException:
		storage.cleanup_images(new_paths)
		raise

	old_paths = []
	commit_started = False

	try:
		lock_product(db, store_id, product_id, user_id)

		if image_id is None:
			images = get_images(db, product_id)

			if len(images) >= 5:
				raise HTTPException(status_code=409, detail='O produto pode ter no máximo cinco imagens.')

			set_positions(db, images)
			image = ProductImage(product_id=product_id, storage_path=new_path, position=len(images) + 1)
			db.add(image)
		else:
			image = get_image(db, product_id, image_id)
			old_paths = list(storage.image_paths(image.storage_path).values())
			image.storage_path = new_path

		db.flush()
		response = build_image_response(image)
		commit_started = True
		db.commit()
	except HTTPException:
		db.rollback()
		storage.cleanup_images(new_paths)
		raise
	except SQLAlchemyError as error:
		db.rollback()

		if not commit_started or isinstance(error, IntegrityError):
			storage.cleanup_images(new_paths)
		else:
			logger.error('Commit de imagem de produto incerto; arquivos preservados: %s', new_paths)

		raise HTTPException(status_code=503, detail='Não foi possível salvar a imagem do produto.') from None

	storage.cleanup_images(old_paths)
	return response


def remove_image(db: Session, store_id: UUID, product_id: UUID, user_id: UUID, image_id: UUID) -> None:
	lock_product(db, store_id, product_id, user_id)
	image = get_image(db, product_id, image_id)
	paths = list(storage.image_paths(image.storage_path).values())

	try:
		db.delete(image)
		db.flush()
		set_positions(db, get_images(db, product_id))
		db.commit()
	except SQLAlchemyError:
		db.rollback()
		raise HTTPException(status_code=503, detail='Não foi possível remover a imagem do produto.') from None

	storage.cleanup_images(paths)


def reorder_images(db: Session, store_id: UUID, product_id: UUID, user_id: UUID, data: ProductImageOrder) -> list[ProductImageResponse]:
	lock_product(db, store_id, product_id, user_id)
	images = {image.id: image for image in get_images(db, product_id)}

	if set(data.image_ids) != set(images):
		raise HTTPException(status_code=422, detail='Informe todas as imagens deste produto, sem adicionar ou omitir ids.')

	ordered = [images[image_id] for image_id in data.image_ids]
	set_positions(db, ordered)
	response = [build_image_response(image) for image in ordered]
	db.commit()
	return response

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.products import storage
from app.modules.products.models import Product, ProductImage, ProductSize
from app.modules.products.schemas import ProductCreate, ProductImageResponse, ProductImageVariantResponse, ProductResponse, ProductSizeCreate, ProductSizeResponse, ProductSizeUpdate, ProductUpdate
from app.modules.stores.service import get_store, lock_store, require_store_member


def get_store_product(db: Session, store_id: UUID, product_id: UUID) -> Product:
	# Conferir os dois ids impede administrar um produto usando a rota de outra loja.
	product = db.scalar(select(Product).where(Product.id == product_id, Product.store_id == store_id))

	if not product:
		raise HTTPException(status_code=404, detail='Produto não encontrado nesta loja.')

	return product


def require_product_member(db: Session, store_id: UUID, product_id: UUID, user_id: UUID) -> Product:
	get_store(db, store_id)
	require_store_member(db, store_id, user_id)
	return get_store_product(db, store_id, product_id)


def lock_product(db: Session, store_id: UUID, product_id: UUID, user_id: UUID) -> Product:
	lock_store(db, store_id)
	require_store_member(db, store_id, user_id)
	return get_store_product(db, store_id, product_id)


def build_image_response(image: ProductImage) -> ProductImageResponse:
	variants = {name: ProductImageVariantResponse(url=storage.get_image_url(path)) for name, path in storage.image_paths(image.storage_path).items()}
	return ProductImageResponse(id=image.id, position=image.position, variants=variants)


def build_product_responses(db: Session, products: list[Product]) -> list[ProductResponse]:
	if not products:
		return []

	product_ids = [product.id for product in products]
	# Duas consultas em lote para tamanhos/imagens, sem consultas por produto ou por variante.
	sizes = db.scalars(select(ProductSize).where(ProductSize.product_id.in_(product_ids), ProductSize.available.is_(True)).order_by(ProductSize.product_id, ProductSize.size)).all()
	images = db.scalars(select(ProductImage).where(ProductImage.product_id.in_(product_ids)).order_by(ProductImage.product_id, ProductImage.position)).all()
	sizes_by_product = {product_id: [] for product_id in product_ids}
	images_by_product = {product_id: [] for product_id in product_ids}

	for size in sizes:
		sizes_by_product[size.product_id].append(ProductSizeResponse.model_validate(size))

	for image in images:
		images_by_product[image.product_id].append(build_image_response(image))

	return [ProductResponse(id=product.id, store_id=product.store_id, name=product.name, price=product.price, description=product.description, sizes=sizes_by_product[product.id], images=images_by_product[product.id]) for product in products]


def list_products(db: Session, store_id: UUID, offset: int, limit: int) -> list[ProductResponse]:
	get_store(db, store_id)
	products = list(db.scalars(select(Product).where(Product.store_id == store_id).order_by(Product.id).offset(offset).limit(limit)).all())
	return build_product_responses(db, products)


def get_product(db: Session, product_id: UUID) -> ProductResponse:
	product = db.get(Product, product_id)

	if not product:
		raise HTTPException(status_code=404, detail='Produto não encontrado.')

	return build_product_responses(db, [product])[0]


def create_product(db: Session, store_id: UUID, user_id: UUID, data: ProductCreate) -> ProductResponse:
	lock_store(db, store_id)
	require_store_member(db, store_id, user_id)
	product = Product(store_id=store_id, **data.model_dump())
	db.add(product)
	db.commit()
	return build_product_responses(db, [product])[0]


def update_product(db: Session, store_id: UUID, product_id: UUID, user_id: UUID, data: ProductUpdate) -> ProductResponse:
	product = lock_product(db, store_id, product_id, user_id)

	for field, value in data.model_dump(exclude_unset=True).items():
		setattr(product, field, value)

	db.commit()
	return build_product_responses(db, [product])[0]


def delete_product(db: Session, store_id: UUID, product_id: UUID, user_id: UUID) -> None:
	product = lock_product(db, store_id, product_id, user_id)
	images = db.scalars(select(ProductImage).where(ProductImage.product_id == product.id)).all()
	paths = [path for image in images for path in storage.image_paths(image.storage_path).values()]

	try:
		db.delete(product)
		db.commit()
	except SQLAlchemyError:
		db.rollback()
		raise HTTPException(status_code=503, detail='Não foi possível excluir o produto.') from None

	# O cascade apaga as referências; os arquivos são removidos depois de liberar a transação.
	storage.cleanup_images(paths)


def get_size(db: Session, product_id: UUID, size: str) -> ProductSize:
	row = db.get(ProductSize, (product_id, size))

	if not row:
		raise HTTPException(status_code=404, detail='Tamanho não encontrado neste produto.')

	return row


def add_size(db: Session, store_id: UUID, product_id: UUID, user_id: UUID, data: ProductSizeCreate) -> ProductSize:
	lock_product(db, store_id, product_id, user_id)

	if db.get(ProductSize, (product_id, data.size)):
		raise HTTPException(status_code=409, detail='Tamanho já cadastrado neste produto.')

	size = ProductSize(product_id=product_id, **data.model_dump())
	db.add(size)

	try:
		db.commit()
	except IntegrityError as error:
		db.rollback()

		if error.orig.diag.constraint_name == 'product_sizes_pkey':
			raise HTTPException(status_code=409, detail='Tamanho já cadastrado neste produto.') from None

		raise

	return size


def update_size(db: Session, store_id: UUID, product_id: UUID, user_id: UUID, size: str, data: ProductSizeUpdate) -> ProductSize:
	lock_product(db, store_id, product_id, user_id)
	row = get_size(db, product_id, size)
	# Indisponibilidade altera apenas o booleano, preservando o tamanho cadastrado.
	row.available = data.available
	db.commit()
	return row


def remove_size(db: Session, store_id: UUID, product_id: UUID, user_id: UUID, size: str) -> None:
	lock_product(db, store_id, product_id, user_id)
	row = get_size(db, product_id, size)
	db.delete(row)
	db.commit()

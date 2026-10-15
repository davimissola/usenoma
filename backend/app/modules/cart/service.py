from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.cart.models import Cart, CartItem
from app.modules.cart.schemas import MAX_QUANTITY, CartItemCreate, CartItemResponse, CartItemUpdate, CartProductResponse, CartResponse, CartStoreResponse
from app.modules.products.models import Product, ProductImage, ProductSize
from app.modules.products.service import build_image_response
from app.modules.stores.models import Store, StoreImage, StoreImageVariant
from app.modules.stores.storage import get_store_image_url
from app.modules.users.models import User


def get_user_cart(db: Session, user_id: UUID, lock: bool = False) -> Cart | None:
	user_query = select(User.id).where(User.id == user_id)

	if lock:
		# Serializa as escritas do usuário, inclusive quando seu carrinho ainda não existe.
		user_query = user_query.with_for_update()

	if db.scalar(user_query) is None:
		raise HTTPException(status_code=401, detail='Usuário não encontrado.', headers={'WWW-Authenticate': 'Bearer'})

	return db.scalar(select(Cart).where(Cart.user_id == user_id))


def build_cart_response(db: Session, cart: Cart | None) -> CartResponse:
	if cart is None:
		return CartResponse(id=None, updated_at=None, items=[])

	# O outer join mantém itens de produtos/tamanhos removidos. Não há consultas por item.
	rows = db.execute(select(Cart.updated_at, CartItem, Product, ProductSize, Store).select_from(Cart).outerjoin(CartItem, CartItem.cart_id == Cart.id).outerjoin(Product, Product.id == CartItem.product_id).outerjoin(ProductSize, (ProductSize.product_id == CartItem.product_id) & (ProductSize.size == CartItem.size)).outerjoin(Store, Store.id == Product.store_id).where(Cart.id == cart.id).order_by(CartItem.id)).all()

	if not rows:
		return CartResponse(id=None, updated_at=None, items=[])

	product_ids = {row.Product.id for row in rows if row.Product is not None}
	store_ids = {row.Store.id for row in rows if row.Store is not None}
	primary_images = {}
	available_sizes = {}
	store_logos = {}

	if store_ids:
		# Busca as logos em lote; vários itens da mesma loja compartilham a mesma URL.
		logos = db.execute(select(StoreImage.store_id, StoreImageVariant.variant, StoreImageVariant.storage_path).join(StoreImageVariant, StoreImageVariant.store_image_id == StoreImage.id).where(StoreImage.store_id.in_(store_ids), StoreImage.type == 'logo')).all()
		logo_paths = {}
		for store_id, variant, storage_path in logos:
			logo_paths.setdefault(store_id, {})[variant] = storage_path

		for store_id, variants in logo_paths.items():
			# Imagens antigas podem ter apenas uma variante, inclusive PNG ou JPEG.
			storage_path = variants.get('small') or variants.get('medium') or variants.get('large')
			if storage_path:
				store_logos[store_id] = get_store_image_url(storage_path)

	if product_ids:
		# A tela pode trocar o tamanho sem buscar cada produto separadamente.
		sizes = db.scalars(select(ProductSize).where(ProductSize.product_id.in_(product_ids), ProductSize.available.is_(True)).order_by(ProductSize.size)).all()
		for size in sizes:
			available_sizes.setdefault(size.product_id, []).append(size.size)

		images = db.scalars(select(ProductImage).where(ProductImage.product_id.in_(product_ids)).order_by(ProductImage.product_id, ProductImage.position)).all()

		for image in images:
			if image.product_id not in primary_images:
				primary_images[image.product_id] = build_image_response(image)

	items = []

	for _, item, product, size, store in rows:
		if item is None:
			continue

		product_response = None
		store_response = None
		unit_price = None
		subtotal = None
		unavailable_reason = 'product_removed'

		if product is not None:
			product_response = CartProductResponse(id=product.id, name=product.name, description=product.description, sizes=available_sizes.get(product.id, []))
			store_response = CartStoreResponse(id=store.id, name=store.name, slug=store.slug, description=store.description, logo_url=store_logos.get(store.id))
			unit_price = product.price
			subtotal = product.price * item.quantity

			if size is None:
				unavailable_reason = 'size_removed'
			elif not size.available:
				unavailable_reason = 'size_unavailable'
			else:
				unavailable_reason = None

		items.append(CartItemResponse(id=item.id, product_id=item.product_id, product=product_response, image=primary_images.get(item.product_id), size=item.size, quantity=item.quantity, unit_price=unit_price, subtotal=subtotal, store=store_response, available=unavailable_reason is None, unavailable_reason=unavailable_reason))

	return CartResponse(id=cart.id, updated_at=rows[0].updated_at, items=items)


def get_cart(db: Session, user_id: UUID) -> CartResponse:
	return build_cart_response(db, get_user_cart(db, user_id))


def validate_product_size(db: Session, product_id: UUID | None, size: str) -> None:
	product = db.scalar(select(Product.id).where(Product.id == product_id).with_for_update(read=True))

	if product is None:
		raise HTTPException(status_code=404, detail='Produto não encontrado.')

	# Mantém produto/tamanho válidos até o commit, sem reservar quantidade ou estoque.
	product_size = db.scalar(select(ProductSize).where(ProductSize.product_id == product_id, ProductSize.size == size).with_for_update(read=True))

	if product_size is None:
		raise HTTPException(status_code=404, detail='Tamanho não encontrado neste produto.')

	if not product_size.available:
		raise HTTPException(status_code=409, detail='Tamanho indisponível neste produto.')


def get_cart_item(db: Session, cart: Cart | None, item_id: UUID) -> CartItem:
	if cart is not None:
		item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id))
		if item is not None:
			return item

	raise HTTPException(status_code=404, detail='Item não encontrado no seu carrinho.')


def add_item(db: Session, user_id: UUID, data: CartItemCreate) -> CartResponse:
	cart = get_user_cart(db, user_id, lock=True)
	validate_product_size(db, data.product_id, data.size)

	if cart is None:
		cart = Cart(user_id=user_id)
		db.add(cart)
		db.flush()

	item = db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == data.product_id, CartItem.size == data.size))

	if item is not None:
		quantity = item.quantity + data.quantity
		if quantity > MAX_QUANTITY:
			raise HTTPException(status_code=422, detail='A quantidade excede o limite permitido.')
		item.quantity = quantity
	else:
		db.add(CartItem(cart_id=cart.id, **data.model_dump()))

	cart.updated_at = datetime.now(timezone.utc)
	db.flush()
	response = build_cart_response(db, cart)
	db.commit()
	return response


def update_item(db: Session, user_id: UUID, item_id: UUID, data: CartItemUpdate) -> CartResponse:
	cart = get_user_cart(db, user_id, lock=True)
	item = get_cart_item(db, cart, item_id)
	size = item.size
	quantity = item.quantity

	if data.size is not None:
		size = data.size
	if data.quantity is not None:
		quantity = data.quantity

	if size == item.size and quantity == item.quantity:
		return build_cart_response(db, cart)

	validate_product_size(db, item.product_id, size)
	target = db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == item.product_id, CartItem.size == size))

	if target is not None and target.id != item.id:
		# A quantidade do PATCH substitui a do item de origem antes de somar ao destino.
		quantity += target.quantity
		if quantity > MAX_QUANTITY:
			raise HTTPException(status_code=422, detail='A quantidade excede o limite permitido.')
		target.quantity = quantity
		db.delete(item)
	else:
		item.size = size
		item.quantity = quantity

	cart.updated_at = datetime.now(timezone.utc)
	db.flush()
	response = build_cart_response(db, cart)
	db.commit()
	return response


def remove_item(db: Session, user_id: UUID, item_id: UUID) -> None:
	cart = get_user_cart(db, user_id, lock=True)
	item = get_cart_item(db, cart, item_id)
	db.delete(item)
	cart.updated_at = datetime.now(timezone.utc)
	db.commit()


def clear_cart(db: Session, user_id: UUID) -> None:
	cart = get_user_cart(db, user_id, lock=True)

	if cart is None:
		return

	result = db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))

	if result.rowcount:
		cart.updated_at = datetime.now(timezone.utc)
		db.commit()

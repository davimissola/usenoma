from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.modules.products.schemas import ProductImageResponse, ProductSizeName
from app.modules.stores.schemas import StoreResponse


# Limite do Integer do PostgreSQL, sem impor uma regra de estoque ou de compra.
MAX_QUANTITY = 2_147_483_647
CartQuantity = Annotated[int, Field(strict=True, ge=1, le=MAX_QUANTITY)]


class CartItemCreate(BaseModel):
	model_config = ConfigDict(extra='forbid')

	product_id: UUID
	size: ProductSizeName
	quantity: CartQuantity


class CartItemUpdate(BaseModel):
	model_config = ConfigDict(extra='forbid')

	size: ProductSizeName | None = None
	quantity: CartQuantity | None = None

	@field_validator('size', 'quantity')
	@classmethod
	def validate_required_fields(cls, value: str | int | None) -> str | int:
		if value is None:
			raise ValueError('Tamanho e quantidade não podem ser nulos.')

		return value


class CartProductResponse(BaseModel):
	id: UUID
	name: str
	description: str | None
	sizes: list[str]


class CartStoreResponse(StoreResponse):
	logo_url: str | None = None


class CartItemResponse(BaseModel):
	id: UUID
	product_id: UUID | None
	product: CartProductResponse | None
	image: ProductImageResponse | None
	size: str
	quantity: int
	unit_price: Decimal | None
	subtotal: Decimal | None
	store: CartStoreResponse | None
	available: bool
	unavailable_reason: Literal['product_removed', 'size_removed', 'size_unavailable'] | None

	@field_serializer('unit_price', 'subtotal')
	def serialize_money(self, value: Decimal | None) -> str | None:
		if value is None:
			return None

		return format(value, '.2f')


class CartResponse(BaseModel):
	id: UUID | None
	updated_at: datetime | None
	items: list[CartItemResponse]

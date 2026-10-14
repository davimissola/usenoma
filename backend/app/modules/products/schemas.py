from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, field_serializer, field_validator


ProductName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
ProductPrice = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2, allow_inf_nan=False)]

def uppercase_size(value: object) -> object:
	if isinstance(value, str):
		return value.upper()

	return value


# Valida o comprimento depois de normalizar, inclusive quando Unicode expande os caracteres.
ProductSizeName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20), BeforeValidator(uppercase_size)]


class ProductCreate(BaseModel):
	model_config = ConfigDict(extra='forbid')

	name: ProductName
	price: ProductPrice
	description: str | None = None


class ProductUpdate(BaseModel):
	model_config = ConfigDict(extra='forbid')

	name: ProductName | None = None
	price: ProductPrice | None = None
	description: str | None = None

	@field_validator('name', 'price')
	@classmethod
	def validate_required_fields(cls, value: str | Decimal | None) -> str | Decimal:
		if value is None:
			raise ValueError('Nome e preço não podem ser nulos.')

		return value


class ProductSizeCreate(BaseModel):
	model_config = ConfigDict(extra='forbid')

	size: ProductSizeName
	available: bool = Field(default=True, strict=True)


class ProductSizeUpdate(BaseModel):
	model_config = ConfigDict(extra='forbid')

	available: bool = Field(strict=True)


class ProductSizeResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	size: str
	available: bool


class ProductImageVariantResponse(BaseModel):
	url: str


class ProductImageResponse(BaseModel):
	id: UUID
	position: int
	variants: dict[Literal['card', 'large'], ProductImageVariantResponse]


class ProductImageOrder(BaseModel):
	model_config = ConfigDict(extra='forbid')

	image_ids: list[UUID] = Field(max_length=4)

	@field_validator('image_ids')
	@classmethod
	def validate_unique_images(cls, value: list[UUID]) -> list[UUID]:
		if len(value) != len(set(value)):
			raise ValueError('Cada imagem deve aparecer uma única vez.')

		return value


class ProductResponse(BaseModel):
	id: UUID
	store_id: UUID
	name: str
	price: Decimal
	description: str | None
	sizes: list[ProductSizeResponse]
	images: list[ProductImageResponse]

	@field_serializer('price')
	def serialize_price(self, value: Decimal) -> str:
		return format(value, '.2f')

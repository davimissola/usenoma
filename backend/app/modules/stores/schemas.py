from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator


StoreName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
StoreSlug = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120, pattern=r'^[a-z0-9]+(-[a-z0-9]+)*$')]
StoreRole = Literal['owner', 'manager']


class StoreCreate(BaseModel):
	model_config = ConfigDict(extra='forbid')

	name: StoreName
	slug: StoreSlug
	description: str | None = None


class StoreUpdate(BaseModel):
	model_config = ConfigDict(extra='forbid')

	name: StoreName | None = None
	slug: StoreSlug | None = None
	description: str | None = None

	@field_validator('name', 'slug')
	@classmethod
	def validate_required_fields(cls, value: str | None) -> str:
		# Campos ausentes podem manter o valor atual; enviar null para nome ou slug não pode.
		if value is None:
			raise ValueError('Nome e slug não podem ser nulos.')

		return value


class StoreResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	name: str
	slug: str
	description: str | None


class StoreMemberCreate(BaseModel):
	model_config = ConfigDict(extra='forbid')

	user_id: UUID
	role: StoreRole


class StoreMemberUpdate(BaseModel):
	model_config = ConfigDict(extra='forbid')

	role: StoreRole


class StoreMemberResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	user_id: UUID
	username: str
	role: StoreRole

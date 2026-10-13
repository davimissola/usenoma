from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserStoreResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	name: str
	slug: str


class UserResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	username: str
	email: str
	stores: list[UserStoreResponse]

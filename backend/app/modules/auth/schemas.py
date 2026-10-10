from typing import Literal

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator


class RegisterRequest(BaseModel):
	username: str = Field(min_length=3, max_length=30, pattern=r'^[A-Za-z0-9_.]+$')
	email: EmailStr = Field(max_length=254)
	password: SecretStr = Field(min_length=8, max_length=128)

	@field_validator('username', mode='before')
	@classmethod
	def normalize_username(cls, value: str) -> str:
		if isinstance(value, str):
			return value.strip() 
		else:
			return value

	@field_validator('email')
	@classmethod
	def normalize_email(cls, value: str) -> str:
		return value.lower()


class TokenResponse(BaseModel):
	access_token: str
	token_type: Literal['bearer'] = 'bearer'

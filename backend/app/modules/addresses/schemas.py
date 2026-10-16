import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, field_validator


def normalize_postal_code(value: object) -> object:
	if isinstance(value, str):
		value = value.strip()
		if re.fullmatch(r'[0-9]{5}-?[0-9]{3}', value):
			return value.replace('-', '')

	return value


def normalize_phone(value: object) -> object:
	if isinstance(value, str):
		value = value.strip()
		if re.fullmatch(r'(?:\+55\s*)?[0-9() .-]+', value):
			digits = re.sub(r'[^0-9]', '', value)
			# Persiste DDD + número, aceitando também a entrada com o código +55.
			if len(digits) in (12, 13) and digits.startswith('55'):
				digits = digits[2:]
			return digits

	return value


def normalize_state(value: object) -> object:
	if isinstance(value, str):
		return value.strip().upper()

	return value


def normalize_complement(value: object) -> object:
	if isinstance(value, str):
		value = value.strip()
		if not value:
			return None

	return value


RecipientName = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=120)]
PostalCode = Annotated[str, StringConstraints(strict=True, pattern=r'^[0-9]{8}$'), BeforeValidator(normalize_postal_code)]
Street = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)]
AddressNumber = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=20)]
Complement = Annotated[str | None, Field(max_length=120), BeforeValidator(normalize_complement)]
Neighborhood = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=120)]
City = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=120)]
BrazilState = Annotated[Literal['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'], BeforeValidator(normalize_state)]
Phone = Annotated[str, StringConstraints(strict=True, pattern=r'^[0-9]{10,11}$'), BeforeValidator(normalize_phone)]


class UserAddressCreate(BaseModel):
	model_config = ConfigDict(extra='forbid')

	recipient_name: RecipientName
	postal_code: PostalCode
	street: Street
	number: AddressNumber
	complement: Complement = None
	neighborhood: Neighborhood
	city: City
	state: BrazilState
	phone: Phone
	is_default: bool = Field(default=False, strict=True)


class UserAddressUpdate(BaseModel):
	model_config = ConfigDict(extra='forbid')

	recipient_name: RecipientName | None = None
	postal_code: PostalCode | None = None
	street: Street | None = None
	number: AddressNumber | None = None
	complement: Complement = None
	neighborhood: Neighborhood | None = None
	city: City | None = None
	state: BrazilState | None = None
	phone: Phone | None = None
	is_default: bool | None = Field(default=None, strict=True)

	@field_validator('recipient_name', 'postal_code', 'street', 'number', 'neighborhood', 'city', 'state', 'phone', 'is_default')
	@classmethod
	def validate_required_fields(cls, value: str | bool | None) -> str | bool:
		# Omitir mantém o valor atual; somente complement pode ser limpo com null.
		if value is None:
			raise ValueError('Este campo não pode ser nulo.')

		return value


class UserAddressResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	recipient_name: str
	postal_code: str
	street: str
	number: str
	complement: str | None
	neighborhood: str
	city: str
	state: str
	phone: str
	is_default: bool

from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / '.env', env_file_encoding='utf-8', extra='ignore', hide_input_in_errors=True)

	database_url: str
	secret_key: SecretStr
	frontend_url: str = 'http://localhost:5173'
	access_token_expire_minutes: int = Field(default=30, gt=0)
	refresh_token_expire_days: int = Field(default=30, gt=0)
	cookie_secure: bool = True

	@field_validator('database_url')
	@classmethod
	def validate_database_url(cls, value: str) -> str:
		try:
			url = make_url(value)
		except (ArgumentError, ValueError) as error:
			raise ValueError('DATABASE_URL deve ser uma URL PostgreSQL válida.') from error

		if url.get_backend_name() != 'postgresql' or not url.host or not url.database:
			raise ValueError('DATABASE_URL deve usar PostgreSQL e informar o host e o banco.')

		return value

	@field_validator('secret_key')
	@classmethod
	def validate_secret_key(cls, value: SecretStr) -> SecretStr:
		if len(value.get_secret_value().encode()) < 32:
			raise ValueError('SECRET_KEY deve ter pelo menos 32 bytes.')

		return value

	@field_validator('frontend_url')
	@classmethod
	def normalize_frontend_url(cls, value: str) -> str:
		value = value.strip().rstrip('/')
		url = urlsplit(value)

		if url.scheme not in {'http', 'https'} or not url.hostname or url.username is not None or url.path or url.query or url.fragment:
			raise ValueError('FRONTEND_URL deve ser a origem HTTP ou HTTPS do frontend, sem caminho, credenciais, query ou fragmento.')

		return value


settings = Settings()

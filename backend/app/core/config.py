from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / '.env', env_file_encoding='utf-8', extra='ignore')

	database_url: str
	secret_key: SecretStr
	frontend_url: str = 'http://localhost:5173'
	access_token_expire_minutes: int = Field(default=30, gt=0)
	refresh_token_expire_days: int = Field(default=30, gt=0)
	cookie_secure: bool = True

	@field_validator('secret_key')
	@classmethod
	def validate_secret_key(cls, value: SecretStr) -> SecretStr:
		if len(value.get_secret_value().encode()) < 32:
			raise ValueError('SECRET_KEY deve ter pelo menos 32 bytes.')

		return value

	@field_validator('frontend_url')
	@classmethod
	def normalize_frontend_url(cls, value: str) -> str:
		return value.rstrip('/')


settings = Settings()

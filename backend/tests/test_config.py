import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_invalid_database_configuration_does_not_expose_credentials():
	with pytest.raises(ValidationError) as error:
		Settings(_env_file=None, database_url='mysql://postgres:SenhaPrivadaDaConfiguracao@localhost/noma')

	assert 'DATABASE_URL' in str(error.value)
	assert 'SenhaPrivadaDaConfiguracao' not in str(error.value)


@pytest.mark.parametrize('frontend_url', ['https://noma.test/acesso', 'https://noma.test?token=privado', 'https://usuario:senha@noma.test', 'ftp://noma.test'])
def test_frontend_configuration_requires_an_http_origin(frontend_url):
	with pytest.raises(ValidationError):
		Settings(_env_file=None, frontend_url=frontend_url)


@pytest.mark.parametrize('supabase_url', ['http://project.supabase.co', 'https://project.supabase.co/storage', 'https://usuario:senha@project.supabase.co', 'https://project.supabase.co?key=privado'])
def test_storage_configuration_requires_a_safe_https_origin(supabase_url):
	with pytest.raises(ValidationError):
		Settings(_env_file=None, supabase_url=supabase_url)


def test_storage_key_is_masked_in_settings_and_url_is_normalized():
	config = Settings(_env_file=None, supabase_url=' https://project.supabase.co/ ', supabase_secret_key='sb_secret_valor_que_nao_pode_aparecer')

	assert config.supabase_url == 'https://project.supabase.co'
	assert 'sb_secret_valor_que_nao_pode_aparecer' not in repr(config)

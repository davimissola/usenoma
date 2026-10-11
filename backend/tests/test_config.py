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

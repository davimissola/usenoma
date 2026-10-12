from unittest.mock import Mock

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.core.config import settings
from app.modules.stores import storage


@pytest.fixture
def storage_settings(monkeypatch):
	monkeypatch.setattr(settings, 'supabase_url', 'https://project.supabase.co')
	monkeypatch.setattr(settings, 'supabase_secret_key', SecretStr('sb_secret_teste_privado'))
	monkeypatch.setattr(settings, 'supabase_storage_bucket', 'store-media')


def test_supabase_upload_sends_original_bytes_with_private_key_and_without_overwrite(storage_settings, monkeypatch):
	request = httpx.Request('POST', 'https://project.supabase.co/storage/v1/object/store-media/stores/test/logo.png')
	post = Mock(return_value=httpx.Response(200, request=request))
	monkeypatch.setattr(storage.httpx, 'post', post)

	storage.upload_store_image('stores/test/logo.png', b'bytes-da-imagem', 'image/png')

	post.assert_called_once_with(str(request.url), content=b'bytes-da-imagem', headers={'apikey': 'sb_secret_teste_privado', 'Content-Type': 'image/png', 'x-upsert': 'false'}, timeout=30)


def test_supabase_delete_targets_only_the_requested_path(storage_settings, monkeypatch):
	request = httpx.Request('DELETE', 'https://project.supabase.co/storage/v1/object/store-media')
	delete = Mock(return_value=httpx.Response(200, request=request))
	monkeypatch.setattr(storage.httpx, 'request', delete)

	storage.delete_store_image('stores/test/logo.png')

	delete.assert_called_once_with('DELETE', str(request.url), json={'prefixes': ['stores/test/logo.png']}, headers={'apikey': 'sb_secret_teste_privado'}, timeout=30)


@pytest.mark.parametrize('operation', ['upload', 'delete'])
def test_storage_errors_do_not_expose_remote_body_or_key(storage_settings, monkeypatch, caplog, operation):
	request = httpx.Request('POST', 'https://project.supabase.co')
	response = httpx.Response(500, request=request, text='sb_secret_teste_privado erro interno do Supabase')
	monkeypatch.setattr(storage.httpx, 'post', Mock(return_value=response))
	monkeypatch.setattr(storage.httpx, 'request', Mock(return_value=response))

	with pytest.raises(HTTPException) as error:
		if operation == 'upload':
			storage.upload_store_image('stores/test/logo.png', b'bytes', 'image/png')
		else:
			storage.delete_store_image('stores/test/logo.png')

	assert error.value.status_code == 503
	assert 'sb_secret' not in error.value.detail
	assert 'erro interno' not in error.value.detail
	assert 'sb_secret' not in caplog.text


def test_upload_timeout_returns_safe_error(storage_settings, monkeypatch):
	monkeypatch.setattr(storage.httpx, 'post', Mock(side_effect=httpx.TimeoutException('sb_secret_teste_privado')))

	with pytest.raises(HTTPException) as error:
		storage.upload_store_image('stores/test/logo.png', b'bytes', 'image/png')

	assert error.value.status_code == 503
	assert 'sb_secret' not in error.value.detail


def test_unconfigured_storage_does_not_make_external_requests(monkeypatch):
	monkeypatch.setattr(settings, 'supabase_secret_key', None)
	post = Mock()
	monkeypatch.setattr(storage.httpx, 'post', post)

	with pytest.raises(HTTPException) as error:
		storage.upload_store_image('stores/test/logo.png', b'bytes', 'image/png')

	assert error.value.status_code == 503
	post.assert_not_called()

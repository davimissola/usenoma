import httpx
from fastapi import HTTPException

from app.core.config import settings


def upload_store_image(storage_path: str, data: bytes, mime_type: str) -> None:
	# Recebe bytes já processados; esta função cuida apenas da chamada ao Supabase.
	if not settings.supabase_url or not settings.supabase_secret_key or not settings.supabase_secret_key.get_secret_value():
		raise HTTPException(status_code=503, detail='Storage não configurado.')

	# A chave nova do Supabase vai em apikey; o JWT da NOMA nunca é enviado ao Storage.
	headers = {'apikey': settings.supabase_secret_key.get_secret_value(), 'Content-Type': mime_type, 'x-upsert': 'false'}

	try:
		response = httpx.post(f'{settings.supabase_url}/storage/v1/object/{settings.supabase_storage_bucket}/{storage_path}', content=data, headers=headers, timeout=30)
		response.raise_for_status()
	except httpx.HTTPError:
		# Não propaga corpo, headers ou exceções externas, que podem conter informações privadas.
		raise HTTPException(status_code=503, detail='Não foi possível enviar a imagem ao Storage.') from None


def delete_store_image(storage_path: str) -> None:
	# Exclusão física pelo Storage; apagar só a referência no PostgreSQL não remove o arquivo.
	if not settings.supabase_url or not settings.supabase_secret_key or not settings.supabase_secret_key.get_secret_value():
		raise HTTPException(status_code=503, detail='Storage não configurado.')

	try:
		response = httpx.request('DELETE', f'{settings.supabase_url}/storage/v1/object/{settings.supabase_storage_bucket}', json={'prefixes': [storage_path]}, headers={'apikey': settings.supabase_secret_key.get_secret_value()}, timeout=30)
		response.raise_for_status()
	except httpx.HTTPError:
		raise HTTPException(status_code=503, detail='Não foi possível remover a imagem do Storage.') from None

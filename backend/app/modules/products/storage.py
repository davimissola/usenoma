import logging
from pathlib import PurePosixPath

from fastapi import HTTPException

from app.modules.stores.storage import delete_store_image as delete_image, get_store_image_url as get_image_url, upload_store_image as upload_image


logger = logging.getLogger(__name__)


def image_paths(storage_path: str) -> dict[str, str]:
	# O banco aponta para large.webp; card.webp fica na mesma pasta única daquele envio.
	return {'card': str(PurePosixPath(storage_path).with_name('card.webp')), 'large': storage_path}


def cleanup_images(storage_paths: list[str]) -> None:
	for storage_path in dict.fromkeys(storage_paths):
		try:
			delete_image(storage_path)
		except HTTPException:
			logger.warning('Falha ao excluir imagem de produto; arquivo pendente: %s', storage_path)

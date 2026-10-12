import logging
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.stores import storage
from app.modules.stores.image_processing import process_store_image, validate_store_image
from app.modules.stores.models import StoreImage, StoreImageVariant
from app.modules.stores.schemas import StoreImageResponse, StoreImageType, StoreImageVariantResponse
from app.modules.stores.service import get_store, lock_store, require_store_member


logger = logging.getLogger(__name__)


def cleanup_store_image(storage_path: str) -> None:
	try:
		storage.delete_store_image(storage_path)
	except HTTPException:
		# Best effort: o log identifica o arquivo, sem registrar a chave ou a resposta externa.
		logger.warning('Falha ao excluir imagem do Storage; arquivo pendente: %s', storage_path)


def cleanup_store_images(storage_paths: list[str]) -> None:
	# Variantes pequenas podem compartilhar um arquivo; cada path é excluído uma vez.
	for storage_path in dict.fromkeys(storage_paths):
		cleanup_store_image(storage_path)


def upload_image(db: Session, store_id: UUID, user_id: UUID, image_type: StoreImageType, file: UploadFile) -> StoreImageResponse:
	get_store(db, store_id)
	require_store_member(db, store_id, user_id)
	# Encerra a consulta e expira o cache da sessão antes de validar/enviar o arquivo.
	db.rollback()
	processed = process_store_image(validate_store_image(file), image_type)
	folder = f'stores/{store_id}/{image_type}/{uuid4()}'
	new_paths = []
	variant_paths = {}
	size_paths = {}

	try:
		# Todas as variantes já foram processadas; nenhuma chamada de rede mantém transação.
		for variant, (data, width, height) in processed.items():
			dimensions = (width, height)

			if dimensions not in size_paths:
				storage_path = f'{folder}/{variant}.webp'
				# Inclui a tentativa atual: um timeout pode ocorrer depois de receberem o arquivo.
				new_paths.append(storage_path)
				storage.upload_store_image(storage_path, data, 'image/webp')
				size_paths[dimensions] = storage_path

			variant_paths[variant] = size_paths[dimensions]
	except HTTPException:
		cleanup_store_images(new_paths)
		raise

	old_paths = []
	commit_started = False

	try:
		lock_store(db, store_id)
		# O vínculo pode ter sido removido durante o upload; a autorização é consultada de novo.
		require_store_member(db, store_id, user_id)
		image = db.scalar(select(StoreImage).where(StoreImage.store_id == store_id, StoreImage.type == image_type))

		if image:
			# Captura a versão anterior dentro do lock, inclusive quando dois uploads concorrem.
			old_paths = list(db.scalars(select(StoreImageVariant.storage_path).where(StoreImageVariant.store_image_id == image.id)).all())
			db.execute(delete(StoreImageVariant).where(StoreImageVariant.store_image_id == image.id))
		else:
			image = StoreImage(store_id=store_id, type=image_type)
			db.add(image)
			db.flush()

		response_variants = {}

		for variant, (data, width, height) in processed.items():
			storage_path = variant_paths[variant]
			db.add(StoreImageVariant(store_image_id=image.id, variant=variant, storage_path=storage_path, mime_type='image/webp', width=width, height=height, size_bytes=len(data)))
			response_variants[variant] = StoreImageVariantResponse(url=f'{settings.supabase_url}/storage/v1/object/public/{settings.supabase_storage_bucket}/{storage_path}', mime_type='image/webp', width=width, height=height, size_bytes=len(data))

		db.flush()
		response = StoreImageResponse(id=image.id, store_id=image.store_id, type=image.type, variants=response_variants)
		commit_started = True
		db.commit()
	except HTTPException:
		db.rollback()
		cleanup_store_images(new_paths)
		raise
	except SQLAlchemyError as error:
		db.rollback()

		if not commit_started or isinstance(error, IntegrityError):
			cleanup_store_images(new_paths)
		else:
			# Sem confirmação do commit, excluir o novo arquivo pode quebrar uma referência salva.
			logger.error('Resultado do commit de imagem incerto; arquivos preservados: %s', new_paths)

		raise HTTPException(status_code=503, detail='Não foi possível salvar a referência da imagem.') from None

	cleanup_store_images(old_paths)

	return response


def remove_image(db: Session, store_id: UUID, user_id: UUID, image_type: StoreImageType) -> None:
	storage_paths = []

	try:
		lock_store(db, store_id)
		require_store_member(db, store_id, user_id)
		image = db.scalar(select(StoreImage).where(StoreImage.store_id == store_id, StoreImage.type == image_type))

		if not image:
			db.rollback()
			return

		storage_paths = list(db.scalars(select(StoreImageVariant.storage_path).where(StoreImageVariant.store_image_id == image.id)).all())
		# A FK com CASCADE remove as variantes junto da imagem lógica, sem manter histórico.
		db.delete(image)
		db.commit()
	except SQLAlchemyError:
		db.rollback()
		logger.error('Falha ao persistir remoção de imagem; arquivos preservados: %s', storage_paths)
		raise HTTPException(status_code=503, detail='Não foi possível remover a referência da imagem.') from None

	# A chamada de rede ocorre depois de liberar a transação e o bloqueio da loja.
	cleanup_store_images(storage_paths)

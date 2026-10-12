from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.stores import storage
from app.modules.stores.models import Store, StoreImage, StoreImageVariant, StoreMember
from app.modules.stores.schemas import StoreCreate, StoreImageVariantResponse, StoreMemberCreate, StoreMemberResponse, StoreMemberUpdate, StorePublicResponse, StoreUpdate
from app.modules.users.models import User


def create_store(db: Session, data: StoreCreate, owner_username: str) -> Store:
	user = db.scalar(select(User).where(func.lower(User.username) == owner_username.strip().lower()))

	if not user:
		raise HTTPException(status_code=404, detail='Usuário responsável não encontrado.')

	store = Store(**data.model_dump())

	try:
		db.add(store)
		# O flush gera o id, mas só o commit confirma loja e owner juntos.
		db.flush()
		db.add(StoreMember(store_id=store.id, user_id=user.id, role='owner'))
		db.commit()
	except IntegrityError as error:
		db.rollback()
		constraint = error.orig.diag.constraint_name

		if constraint == 'uq_stores_slug':
			raise HTTPException(status_code=409, detail='Slug já utilizado por outra loja.') from error

		if constraint == 'fk_store_members_user_id':
			raise HTTPException(status_code=404, detail='Usuário responsável não encontrado.') from error

		raise

	return store


def get_store(db: Session, store_id: UUID) -> Store:
	store = db.get(Store, store_id)

	if not store:
		raise HTTPException(status_code=404, detail='Loja não encontrada.')

	return store


def get_store_by_slug(db: Session, slug: str) -> Store:
	store = db.scalar(select(Store).where(Store.slug == slug))

	if not store:
		raise HTTPException(status_code=404, detail='Loja não encontrada.')

	return store


def get_public_store_by_slug(db: Session, slug: str) -> StorePublicResponse:
	store = get_store_by_slug(db, slug)
	# Um único join busca todas as variantes da loja, sem consultas dentro do loop.
	rows = db.execute(select(StoreImage.type, StoreImageVariant).join(StoreImageVariant, StoreImageVariant.store_image_id == StoreImage.id).where(StoreImage.store_id == store.id)).all()
	images = {'logo': None, 'cover': None}

	for image_type, variant in rows:
		if images[image_type] is None:
			images[image_type] = {}

		# Só retorna variantes existentes, inclusive imagens antigas que possuem apenas uma.
		images[image_type][variant.variant] = StoreImageVariantResponse(url=storage.get_store_image_url(variant.storage_path), mime_type=variant.mime_type, width=variant.width, height=variant.height, size_bytes=variant.size_bytes)

	return StorePublicResponse(id=store.id, name=store.name, slug=store.slug, description=store.description, logo=images['logo'], cover=images['cover'])


def lock_store(db: Session, store_id: UUID) -> Store:
	# Toda escrita na loja usa o mesmo bloqueio antes de consultar permissões e owners.
	store = db.scalar(select(Store).where(Store.id == store_id).with_for_update())

	if not store:
		raise HTTPException(status_code=404, detail='Loja não encontrada.')

	return store


def require_store_member(db: Session, store_id: UUID, user_id: UUID) -> StoreMember:
	member = db.get(StoreMember, (store_id, user_id))

	if not member:
		raise HTTPException(status_code=403, detail='Você não tem permissão para administrar esta loja.')

	return member


def require_store_owner(db: Session, store_id: UUID, user_id: UUID) -> None:
	member = require_store_member(db, store_id, user_id)

	if member.role != 'owner':
		raise HTTPException(status_code=403, detail='Somente owners podem gerenciar os responsáveis da loja.')


def get_store_member(db: Session, store_id: UUID, user_id: UUID) -> StoreMember:
	member = db.get(StoreMember, (store_id, user_id))

	if not member:
		raise HTTPException(status_code=404, detail='Responsável não encontrado nesta loja.')

	return member


def check_remaining_owner(db: Session, member: StoreMember) -> None:
	if member.role != 'owner':
		return

	# A loja já está bloqueada: outra alteração de membros espera esta transação terminar.
	owners = db.scalar(select(func.count()).select_from(StoreMember).where(StoreMember.store_id == member.store_id, StoreMember.role == 'owner'))

	if owners <= 1:
		raise HTTPException(status_code=409, detail='A loja precisa manter pelo menos um owner.')


def update_store(db: Session, store_id: UUID, user_id: UUID, data: StoreUpdate) -> Store:
	store = lock_store(db, store_id)
	require_store_member(db, store_id, user_id)

	# Campos ausentes ficam intactos; description: null limpa a descrição.
	for field, value in data.model_dump(exclude_unset=True).items():
		setattr(store, field, value)

	try:
		db.commit()
	except IntegrityError as error:
		db.rollback()

		if error.orig.diag.constraint_name == 'uq_stores_slug':
			raise HTTPException(status_code=409, detail='Slug já utilizado por outra loja.') from error

		raise

	return store


def list_store_members(db: Session, store_id: UUID, user_id: UUID, offset: int, limit: int) -> list[StoreMemberResponse]:
	get_store(db, store_id)
	require_store_owner(db, store_id, user_id)
	rows = db.execute(select(StoreMember.user_id, User.username, StoreMember.role).join(User, User.id == StoreMember.user_id).where(StoreMember.store_id == store_id).order_by(User.username, StoreMember.user_id).offset(offset).limit(limit)).all()

	return [StoreMemberResponse.model_validate(row) for row in rows]


def add_store_member(db: Session, store_id: UUID, current_user_id: UUID, data: StoreMemberCreate) -> StoreMemberResponse:
	lock_store(db, store_id)
	require_store_owner(db, store_id, current_user_id)
	user = db.get(User, data.user_id)

	if not user:
		raise HTTPException(status_code=404, detail='Usuário não encontrado.')

	if db.get(StoreMember, (store_id, data.user_id)):
		raise HTTPException(status_code=409, detail='Usuário já é responsável por esta loja.')

	member = StoreMember(store_id=store_id, user_id=data.user_id, role=data.role)

	try:
		db.add(member)
		db.commit()
	except IntegrityError as error:
		db.rollback()
		constraint = error.orig.diag.constraint_name

		if constraint == 'store_members_pkey':
			raise HTTPException(status_code=409, detail='Usuário já é responsável por esta loja.') from error

		if constraint == 'fk_store_members_user_id':
			raise HTTPException(status_code=404, detail='Usuário não encontrado.') from error

		raise

	return StoreMemberResponse(user_id=member.user_id, username=user.username, role=member.role)


def update_store_member(db: Session, store_id: UUID, current_user_id: UUID, user_id: UUID, data: StoreMemberUpdate) -> StoreMemberResponse:
	lock_store(db, store_id)
	require_store_owner(db, store_id, current_user_id)
	member = get_store_member(db, store_id, user_id)

	if member.role == 'owner' and data.role != 'owner':
		check_remaining_owner(db, member)

	username = db.scalar(select(User.username).where(User.id == user_id))
	member.role = data.role
	db.commit()

	return StoreMemberResponse(user_id=member.user_id, username=username, role=member.role)


def remove_store_member(db: Session, store_id: UUID, current_user_id: UUID, user_id: UUID) -> None:
	lock_store(db, store_id)
	require_store_owner(db, store_id, current_user_id)
	member = get_store_member(db, store_id, user_id)
	check_remaining_owner(db, member)
	db.delete(member)
	db.commit()

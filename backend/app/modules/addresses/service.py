from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.addresses.models import UserAddress
from app.modules.addresses.schemas import UserAddressCreate, UserAddressUpdate
from app.modules.users.models import User


def lock_user(db: Session, user_id: UUID) -> None:
	# Bloqueia o usuário porque ainda pode não existir endereço para bloquear.
	# Todas as escritas dele aguardam esta transação antes de consultar o padrão.
	if db.scalar(select(User.id).where(User.id == user_id).with_for_update()) is None:
		raise HTTPException(status_code=401, detail='Usuário não encontrado.', headers={'WWW-Authenticate': 'Bearer'})


def list_addresses(db: Session, user_id: UUID, offset: int, limit: int) -> list[UserAddress]:
	return list(db.scalars(select(UserAddress).where(UserAddress.user_id == user_id).order_by(UserAddress.is_default.desc(), UserAddress.id).offset(offset).limit(limit)).all())


def get_address(db: Session, user_id: UUID, address_id: UUID) -> UserAddress:
	address = db.scalar(select(UserAddress).where(UserAddress.id == address_id, UserAddress.user_id == user_id))

	if address is None:
		# Também responde 404 quando o id pertence a outra pessoa.
		raise HTTPException(status_code=404, detail='Endereço não encontrado.')

	return address


def create_address(db: Session, user_id: UUID, data: UserAddressCreate) -> UserAddress:
	lock_user(db, user_id)
	values = data.model_dump()
	first_id = db.scalar(select(UserAddress.id).where(UserAddress.user_id == user_id).limit(1))

	if first_id is None:
		values['is_default'] = True

	if values['is_default']:
		# Desmarca antes de marcar o novo, respeitando o índice único durante a troca.
		db.execute(update(UserAddress).where(UserAddress.user_id == user_id, UserAddress.is_default.is_(True)).values(is_default=False))

	address = UserAddress(user_id=user_id, **values)
	db.add(address)
	db.commit()
	return address


def update_address(db: Session, user_id: UUID, address_id: UUID, data: UserAddressUpdate) -> UserAddress:
	lock_user(db, user_id)
	address = get_address(db, user_id, address_id)
	values = data.model_dump(exclude_unset=True)

	if values.get('is_default') is False and address.is_default:
		raise HTTPException(status_code=409, detail='Escolha outro endereço como padrão antes de desmarcar este.')

	if values.get('is_default') is True:
		db.execute(update(UserAddress).where(UserAddress.user_id == user_id, UserAddress.id != address_id, UserAddress.is_default.is_(True)).values(is_default=False))

	for field, value in values.items():
		setattr(address, field, value)

	db.commit()
	return address


def delete_address(db: Session, user_id: UUID, address_id: UUID) -> None:
	lock_user(db, user_id)
	address = get_address(db, user_id, address_id)
	was_default = address.is_default
	db.delete(address)
	# Remove o padrão antes de promover outro, ainda sem confirmar a transação.
	db.flush()

	if was_default:
		replacement = db.scalar(select(UserAddress).where(UserAddress.user_id == user_id).order_by(UserAddress.id).limit(1))
		if replacement is not None:
			replacement.is_default = True

	db.commit()

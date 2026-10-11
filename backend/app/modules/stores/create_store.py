from argparse import ArgumentParser

from fastapi import HTTPException
from pydantic import ValidationError

from app.core.database import SessionLocal
from app.modules.stores.schemas import StoreCreate
from app.modules.stores.service import create_store


def main() -> None:
	parser = ArgumentParser(description='Cria uma loja da NOMA e associa um usuário existente como owner.')
	parser.add_argument('--name', required=True)
	parser.add_argument('--slug', required=True)
	parser.add_argument('--description')
	parser.add_argument('--owner-username', required=True)
	args = parser.parse_args()

	try:
		data = StoreCreate(name=args.name, slug=args.slug, description=args.description)

		with SessionLocal() as db:
			store = create_store(db, data, args.owner_username)
	except ValidationError as error:
		parser.error('; '.join(item['msg'] for item in error.errors()))
	except HTTPException as error:
		parser.error(error.detail)

	print(f'Loja "{store.name}" criada: {store.id} (slug: {store.slug}).')


if __name__ == '__main__':
	main()

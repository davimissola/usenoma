from alembic import context

from app.core.database import Base, engine
from app.modules.auth.models import AuthSession
from app.modules.users.models import User


target_metadata = Base.metadata


def include_name(name: str | None, type_: str, parent_names: dict) -> bool:
	return type_ != 'schema' or name == 'app'


def run_migrations_offline() -> None:
	context.configure(url=engine.url, target_metadata=target_metadata, literal_binds=True, include_schemas=True, include_name=include_name)

	with context.begin_transaction():
		context.run_migrations()


def run_migrations_online() -> None:
	with engine.connect() as connection:
		context.configure(connection=connection, target_metadata=target_metadata, include_schemas=True, include_name=include_name)

		with context.begin_transaction():
			context.run_migrations()


if context.is_offline_mode():
	run_migrations_offline()
else:
	run_migrations_online()

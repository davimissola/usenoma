from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
	metadata = MetaData(schema='app')


database_url = make_url(settings.database_url).set(drivername='postgresql+psycopg')
engine = create_engine(database_url, pool_pre_ping=True, hide_parameters=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
	with SessionLocal() as db:
		yield db


DbSession = Annotated[Session, Depends(get_db)]

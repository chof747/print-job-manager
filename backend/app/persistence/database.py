from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


def sessions() -> Iterator[Session]:
    with SessionFactory() as session:
        yield session

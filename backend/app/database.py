from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if url.startswith("sqlite:///") and ":memory:" not in url:
        from pathlib import Path

        Path(url.removeprefix("sqlite:///" )).expanduser().resolve().parent.mkdir(
            parents=True, exist_ok=True
        )
    return create_engine(url, connect_args=connect_args, future=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


async def get_session() -> AsyncGenerator[Session, None]:
    with SessionLocal() as session:
        yield session

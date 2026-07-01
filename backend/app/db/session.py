from __future__ import annotations

from typing import Tuple

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def create_engine_and_session_factory(
    database_url: str,
) -> Tuple[Engine, sessionmaker[Session]]:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
    )
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    return engine, session_factory


engine, SessionLocal = create_engine_and_session_factory(settings.resolve_database_url())


def get_db():
    with SessionLocal() as session:
        yield session

"""Database engine and session helpers."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


def _prepare_sqlite_path(url: str) -> str:
    if url.startswith("sqlite:///"):
        rel = url.replace("sqlite:///", "", 1)
        p = Path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
    return url


DB_URL = _prepare_sqlite_path(settings.database_url)

engine_kwargs: dict = {"pool_pre_ping": True, "future": True}
if DB_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DB_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401 - ensure models are imported

    Base.metadata.create_all(bind=engine)

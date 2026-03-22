"""Database session helpers for the persistent platform services."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import time
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from core.config import get_settings
from db.base import Base
from database import models as _database_models  # noqa: F401
from models import vehicle as _vehicle_models  # noqa: F401


settings = get_settings()
IS_SQLITE = settings.database_url.startswith("sqlite")

if IS_SQLITE:
    database_path = settings.database_url.removeprefix("sqlite:///")
    if database_path and database_path != ":memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def wait_for_database(max_attempts: int = 10, delay_seconds: float = 2.0) -> None:
    if IS_SQLITE:
        return

    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as error:
            last_error = error
            time.sleep(delay_seconds)
    if last_error is not None:
        raise RuntimeError("Database not ready after retry window") from last_error
    raise RuntimeError("Database not ready after retry window")


def init_database() -> None:
    wait_for_database()
    Base.metadata.create_all(bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping_database() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def database_health_details() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as error:
        return {"status": "error", "detail": str(error)}

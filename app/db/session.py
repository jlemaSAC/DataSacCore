from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import DatabaseSettings, SecondaryDatabaseSettings, get_database_settings, get_secondary_database_settings


def build_database_url(settings: DatabaseSettings | SecondaryDatabaseSettings) -> URL:
    return URL.create(
        "mssql+pyodbc",
        username=settings.user,
        password=settings.password,
        host=settings.host,
        port=settings.port,
        database=settings.name,
        query={
            "driver": settings.driver,
            "Encrypt": settings.encrypt,
            "TrustServerCertificate": settings.trust_server_certificate,
        },
    )


@lru_cache
def get_engine() -> Engine:
    settings = get_database_settings()
    return create_engine(
        build_database_url(settings),
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout,
        pool_recycle=settings.pool_recycle,
        pool_pre_ping=True,
        connect_args={"timeout": settings.query_timeout},
        echo=False,
        future=True,
    )


@lru_cache
def get_secondary_engine() -> Engine:
    settings = get_secondary_database_settings()
    return create_engine(
        build_database_url(settings),
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout,
        pool_recycle=settings.pool_recycle,
        pool_pre_ping=True,
        connect_args={"timeout": settings.query_timeout},
        echo=False,
        future=True,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=get_engine(),
    )


@lru_cache
def get_secondary_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=get_secondary_engine(),
    )


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def get_secondary_db() -> Generator[Session, None, None]:
    db = get_secondary_session_factory()()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> int:
    with get_engine().connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return int(result.scalar_one())

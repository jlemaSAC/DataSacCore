import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


class SettingsError(RuntimeError):
    pass


def _required(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise SettingsError(f"Variable de entorno requerida no definida: {name}")
    return value.strip()


def _optional(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def _optional_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise SettingsError(f"Variable de entorno invalida para entero: {name}") from exc


@dataclass(frozen=True)
class DatabaseSettings:
    user: str
    password: str
    host: str
    port: int
    name: str
    driver: str
    encrypt: str
    trust_server_certificate: str
    pool_size: int
    max_overflow: int
    pool_timeout: int
    pool_recycle: int
    query_timeout: int


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings(
        user=_required("DB_USER"),
        password=_required("DB_PASSWORD"),
        host=_required("DB_HOST"),
        port=_optional_int("DB_PORT", 1433),
        name=_required("DB_NAME"),
        driver=_optional("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        encrypt=_optional("DB_ENCRYPT", "no"),
        trust_server_certificate=_optional("DB_TRUST_SERVER_CERTIFICATE", "no"),
        pool_size=_optional_int("DB_POOL_SIZE", 20),
        max_overflow=_optional_int("DB_MAX_OVERFLOW", 10),
        pool_timeout=_optional_int("DB_POOL_TIMEOUT", 30),
        pool_recycle=_optional_int("DB_POOL_RECYCLE", 1800),
        query_timeout=_optional_int("DB_QUERY_TIMEOUT", 30),
    )

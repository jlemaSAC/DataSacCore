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


def _required_int(name: str) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise SettingsError(f"Variable de entorno requerida no definida: {name}")
    try:
        return int(value.strip())
    except ValueError as exc:
        raise SettingsError(f"Variable de entorno invalida para entero: {name}") from exc


def _optional(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def _optional_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default

    return tuple(item.strip() for item in value.split(",") if item.strip())


def _optional_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise SettingsError(f"Variable de entorno invalida para entero: {name}") from exc


def _optional_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False

    raise SettingsError(f"Variable de entorno invalida para booleano: {name}")


@dataclass(frozen=True)
class AppSettings:
    name: str
    version: str
    environment: str
    check_database_on_startup: bool
    check_mongo_on_startup: bool
    cors_allowed_origins: tuple[str, ...]


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


@dataclass(frozen=True)
class SecondaryDatabaseSettings:
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


@dataclass(frozen=True)
class MongoSettings:
    uri: str
    server_selection_timeout_ms: int
    logs_db: str
    datasac_db: str
    mayor_auxiliar_db: str
    analytic_sac_db: str


@dataclass(frozen=True)
class RedisSettings:
    url: str
    socket_connect_timeout_ms: int
    socket_timeout_ms: int


@dataclass(frozen=True)
class JwtSettings:
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int


@lru_cache
def get_app_settings() -> AppSettings:
    environment = _optional("APP_ENV", "production").lower()
    cors_allowed_origins = _optional_csv("CORS_ALLOWED_ORIGINS", ())

    if environment == "dev":
        cors_allowed_origins = ("*",)

    return AppSettings(
        name=_optional("APP_NAME", "DataSacCore"),
        version=_optional("APP_VERSION", "0.1.0"),
        environment=environment,
        check_database_on_startup=_optional_bool("CHECK_DATABASE_ON_STARTUP", True),
        check_mongo_on_startup=_optional_bool("CHECK_MONGO_ON_STARTUP", True),
        cors_allowed_origins=cors_allowed_origins,
    )


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


@lru_cache
def get_secondary_database_settings() -> SecondaryDatabaseSettings:
    return SecondaryDatabaseSettings(
        user=_optional("ALT_DB_USER", _optional("DB_USER", "")),
        password=_optional("ALT_DB_PASSWORD", _optional("DB_PASSWORD", "")),
        host=_optional("ALT_DB_HOST", _optional("DB_HOST", "")),
        port=_optional_int("ALT_DB_PORT", _optional_int("DB_PORT", 1433)),
        name=_optional("ALT_DB_NAME", "SAC_PROVICIONES"),
        driver=_optional(
            "ALT_DB_DRIVER",
            _optional("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        ),
        encrypt=_optional("ALT_DB_ENCRYPT", _optional("DB_ENCRYPT", "no")),
        trust_server_certificate=_optional(
            "ALT_DB_TRUST_SERVER_CERTIFICATE",
            _optional("DB_TRUST_SERVER_CERTIFICATE", "no"),
        ),
        pool_size=_optional_int("ALT_DB_POOL_SIZE", 10),
        max_overflow=_optional_int("ALT_DB_MAX_OVERFLOW", 5),
        pool_timeout=_optional_int("ALT_DB_POOL_TIMEOUT", 30),
        pool_recycle=_optional_int("ALT_DB_POOL_RECYCLE", 1800),
        query_timeout=_optional_int("ALT_DB_QUERY_TIMEOUT", _optional_int("DB_QUERY_TIMEOUT", 30)),
    )


@lru_cache
def get_mongo_settings() -> MongoSettings:
    return MongoSettings(
        uri=_required("MONGO_URI"),
        server_selection_timeout_ms=_optional_int("MONGO_SERVER_SELECTION_TIMEOUT_MS", 5000),
        logs_db=_optional("MONGO_LOGS_DB_NAME", "logs"),
        datasac_db=_optional("MONGO_DATASAC_DB_NAME", "DataSac"),
        mayor_auxiliar_db=_optional("MONGO_MAYOR_AUXILIAR_DB_NAME", "MayorAuxiliar"),
        analytic_sac_db=_optional("MONGO_ANALYTIC_SAC_DB_NAME", "AnalyticSac"),
    )


@lru_cache
def get_redis_settings() -> RedisSettings:
    return RedisSettings(
        url=_optional("REDIS_URL", ""),
        socket_connect_timeout_ms=_optional_int("REDIS_SOCKET_CONNECT_TIMEOUT_MS", 500),
        socket_timeout_ms=_optional_int("REDIS_SOCKET_TIMEOUT_MS", 1000),
    )


@lru_cache
def get_jwt_settings() -> JwtSettings:
    return JwtSettings(
        secret_key=_required("JWT_SECRET_KEY"),
        algorithm=_required("JWT_ALGORITHM"),
        access_token_expire_minutes=_required_int("JWT_ACCESS_TOKEN_EXPIRE_MINUTES"),
    )

from fastapi.testclient import TestClient

from app.core.settings import get_app_settings, get_database_settings
from app.db.session import get_engine, get_session_factory
from app.main import app
from app.main import verify_database_on_startup

client = TestClient(app)

DB_ENV_VARS = (
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_DRIVER",
    "DB_ENCRYPT",
    "DB_TRUST_SERVER_CERTIFICATE",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_POOL_TIMEOUT",
    "DB_POOL_RECYCLE",
    "DB_QUERY_TIMEOUT",
)


def clear_database_caches() -> None:
    get_database_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


def test_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_check_without_settings(monkeypatch) -> None:
    for env_var in DB_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)
    clear_database_caches()

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json()["detail"]["message"] == "Base de datos no configurada"


def test_startup_database_check_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("CHECK_DATABASE_ON_STARTUP", "false")
    get_app_settings.cache_clear()
    clear_database_caches()

    verify_database_on_startup()

    get_app_settings.cache_clear()
    clear_database_caches()

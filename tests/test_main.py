from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.settings import (
    AppSettings,
    get_app_settings,
    get_database_settings,
    get_mongo_settings,
    get_secondary_database_settings,
)
from app.db.mongo import get_mongo_client, get_mongo_client_sync
from app.db.session import (
    get_engine,
    get_secondary_engine,
    get_secondary_session_factory,
    get_session_factory,
)
from app.main import add_cors_middleware, app
from app.main import (
    verify_database_on_startup,
    verify_mongo_on_startup,
    verify_secondary_database_on_startup,
)
from app.models import import_all_models
from app.modules.auth.dependencies import get_auth_service

client = TestClient(app)
MODELS_DIR = Path("app/models")

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

MONGO_ENV_VARS = (
    "MONGO_URI",
    "MONGO_SERVER_SELECTION_TIMEOUT_MS",
    "MONGO_LOGS_DB_NAME",
    "MONGO_DATASAC_DB_NAME",
    "MONGO_MAYOR_AUXILIAR_DB_NAME",
    "MONGO_ANALYTIC_SAC_DB_NAME",
)


def clear_database_caches() -> None:
    get_database_settings.cache_clear()
    get_secondary_database_settings.cache_clear()
    get_engine.cache_clear()
    get_secondary_engine.cache_clear()
    get_session_factory.cache_clear()
    get_secondary_session_factory.cache_clear()


def clear_mongo_caches() -> None:
    get_mongo_settings.cache_clear()
    get_mongo_client.cache_clear()
    get_mongo_client_sync.cache_clear()


def test_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_menu_completo_endpoint_is_not_registered() -> None:
    response = client.post("/auth/menuCompleto")

    assert response.status_code == 404


def test_auth_status_endpoint_is_not_registered() -> None:
    response = client.get("/auth/status")

    assert response.status_code == 404


def test_auth_menu_endpoint_requires_bearer_token() -> None:
    response = client.get("/auth/menu/data-sac-web")

    assert response.status_code == 401


def test_analytic_admin_endpoint_requires_bearer_token() -> None:
    response = client.get("/analytic/rutas")

    assert response.status_code == 401


def test_analytic_menu_endpoint_requires_bearer_token() -> None:
    response = client.get("/analytic/menu")

    assert response.status_code == 401


def test_analytic_solvencia_endpoint_requires_bearer_token() -> None:
    response = client.post(
        "/analytic/indicadores-financieros/solvencia",
        json={"fecha_corte": "2026-06-16T00:00:00", "id_agencia": 1},
    )

    assert response.status_code == 401


def test_login_response_does_not_include_menu() -> None:
    class FakeAuthService:
        def login(self, login_data: object) -> dict:
            return {
                "puede_ingresar": True,
                "nombre": "John Doe",
                "identificacion": "0102030405",
                "codigo": "jdoe",
                "id_agencia": 1,
                "nombre_agencia": "Matriz",
                "activo": True,
                "roles": [],
                "oficinas_consulta": [],
                "menu": [{"label": "No debe salir"}],
                "token": "token",
                "fecha_sistema": date(2026, 6, 16),
            }

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    try:
        response = client.post("/auth/login", json={"codigo": "jdoe", "clave": "secret"})
    finally:
        app.dependency_overrides.pop(get_auth_service, None)

    assert response.status_code == 200
    assert "menu" not in response.json()


def test_app_settings_dev_allows_all_cors_origins(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")
    get_app_settings.cache_clear()

    settings = get_app_settings()

    assert settings.environment == "dev"
    assert settings.cors_allowed_origins == ("*",)

    get_app_settings.cache_clear()


def test_app_settings_reads_cors_origins_from_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com, https://admin.example.com")
    get_app_settings.cache_clear()

    settings = get_app_settings()

    assert settings.cors_allowed_origins == ("https://app.example.com", "https://admin.example.com")

    get_app_settings.cache_clear()


def test_secondary_database_settings_reuse_primary_connection(monkeypatch) -> None:
    primary_values = {
        "DB_USER": "primary-user",
        "DB_PASSWORD": "primary-password",
        "DB_HOST": "sql.example.internal",
        "DB_PORT": "1444",
        "DB_DRIVER": "ODBC Driver 18 for SQL Server",
        "DB_ENCRYPT": "yes",
        "DB_TRUST_SERVER_CERTIFICATE": "yes",
        "DB_QUERY_TIMEOUT": "45",
    }
    for name, value in primary_values.items():
        monkeypatch.setenv(name, value)
    for name in (
        "ALT_DB_USER",
        "ALT_DB_PASSWORD",
        "ALT_DB_HOST",
        "ALT_DB_PORT",
        "ALT_DB_NAME",
        "ALT_DB_DRIVER",
        "ALT_DB_ENCRYPT",
        "ALT_DB_TRUST_SERVER_CERTIFICATE",
        "ALT_DB_QUERY_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)
    get_secondary_database_settings.cache_clear()

    settings = get_secondary_database_settings()

    assert settings.user == "primary-user"
    assert settings.password == "primary-password"
    assert settings.host == "sql.example.internal"
    assert settings.port == 1444
    assert settings.name == "SAC_PROVICIONES"
    assert settings.driver == "ODBC Driver 18 for SQL Server"
    assert settings.encrypt == "yes"
    assert settings.trust_server_certificate == "yes"
    assert settings.query_timeout == 45

    get_secondary_database_settings.cache_clear()


def test_cors_middleware_allows_any_origin_in_dev() -> None:
    cors_app = FastAPI()

    @cors_app.get("/")
    async def cors_root() -> dict[str, str]:
        return {"status": "ok"}

    add_cors_middleware(
        cors_app,
        AppSettings(
            name="test",
            version="0.1.0",
            environment="dev",
            check_database_on_startup=False,
            check_mongo_on_startup=False,
            cors_allowed_origins=("*",),
        ),
    )
    cors_client = TestClient(cors_app)

    response = cors_client.options(
        "/",
        headers={
            "Origin": "https://any-origin.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers


def test_database_health_check_without_settings(monkeypatch) -> None:
    for env_var in DB_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)
    clear_database_caches()

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json()["detail"]["message"] == "Base de datos no configurada"


def test_mongo_health_check_without_settings(monkeypatch) -> None:
    for env_var in MONGO_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)
    clear_mongo_caches()

    response = client.get("/health/mongo")

    assert response.status_code == 503
    assert response.json()["detail"]["message"] == "MongoDB no configurado"


def test_secondary_database_health_check(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.routers.health.check_secondary_database_connection",
        lambda: 1,
    )

    response = client.get("/health/db-secondary")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database_secondary": "connected",
        "check": 1,
    }


def test_secondary_database_health_check_reports_unavailable(monkeypatch) -> None:
    def fail_connection() -> int:
        raise SQLAlchemyError("connection failed")

    monkeypatch.setattr(
        "app.routers.health.check_secondary_database_connection",
        fail_connection,
    )

    response = client.get("/health/db-secondary")

    assert response.status_code == 503
    assert response.json()["detail"]["message"] == "Base de datos secundaria no disponible"


def test_startup_database_check_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("CHECK_DATABASE_ON_STARTUP", "false")
    get_app_settings.cache_clear()
    clear_database_caches()

    verify_database_on_startup()

    get_app_settings.cache_clear()
    clear_database_caches()


def test_startup_secondary_database_check_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("CHECK_DATABASE_ON_STARTUP", "false")
    monkeypatch.setattr(
        "app.main.check_secondary_database_connection",
        lambda: (_ for _ in ()).throw(AssertionError("No debe intentar conectarse")),
    )
    get_app_settings.cache_clear()
    clear_database_caches()

    verify_secondary_database_on_startup()

    get_app_settings.cache_clear()
    clear_database_caches()


def test_startup_mongo_check_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("CHECK_MONGO_ON_STARTUP", "false")
    get_app_settings.cache_clear()
    clear_mongo_caches()

    verify_mongo_on_startup()

    get_app_settings.cache_clear()
    clear_mongo_caches()


def test_import_all_models_without_database_connection(monkeypatch) -> None:
    for env_var in DB_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)
    clear_database_caches()

    import_all_models()


def test_models_do_not_use_relationships() -> None:
    for model_file in MODELS_DIR.rglob("*.py"):
        source = model_file.read_text()
        assert "relationship" not in source, f"{model_file} should not use relationship"


def test_model_columns_are_single_line() -> None:
    for model_file in MODELS_DIR.rglob("*.py"):
        for line in model_file.read_text().splitlines():
            if "= Column(" in line:
                assert line.count("(") == line.count(")"), f"{model_file} has a multiline Column definition"

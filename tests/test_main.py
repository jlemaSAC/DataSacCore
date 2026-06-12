from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_check_without_settings() -> None:
    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json()["detail"]["message"] == "Base de datos no configurada"

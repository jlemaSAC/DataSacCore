from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.colocacion.diaria_asesores.dependencies import (
    get_colocacion_diaria_asesores_service,
)
from app.modules.negocios.colocacion.diaria_asesores.repositories.sql_colocacion_diaria_asesores_repository import (
    ColocacionAsesorDia,
    ColocacionDiariaData,
)
from app.modules.negocios.colocacion.diaria_asesores.service import (
    ColocacionDiariaAsesoresService,
)
from app.modules.negocios.router import router as negocios_router


class FakeRepository:
    def __init__(self, resultado: ColocacionDiariaData | None) -> None:
        self.resultado = resultado
        self.llamada: tuple[int, date] | None = None

    def obtener_colocaciones(self, *, id_agencia: int, fecha: date):
        self.llamada = id_agencia, fecha
        return self.resultado


def _auth_context() -> AuthContext:
    return AuthContext(
        usuario=UsuarioTokenPayload(
            sub="jdoe",
            usuario="John Doe",
            id_agencia=1,
            fecha_sistema=date(2026, 10, 5),
        ),
        token="token",
    )


def test_resumen_colocacion_diaria_suma_operaciones_y_monto_por_asesor() -> None:
    repository = FakeRepository(
        ColocacionDiariaData(
            id_agencia=4,
            agencia="Ambato",
            asesores=[
                ColocacionAsesorDia("ana", "Ana", 2, 8500.126, 1, 3000),
                ColocacionAsesorDia("carlos", "Carlos", 1, 4100, 2, 6200),
            ],
        )
    )
    service = ColocacionDiariaAsesoresService(repository)

    respuesta = service.obtener(id_agencia=4, auth_context=_auth_context())

    assert repository.llamada == (4, date(2026, 10, 5))
    assert respuesta.id_agencia == 4
    assert respuesta.fecha_ayer == date(2026, 10, 4)
    assert respuesta.resumen.hoy.operaciones == 3
    assert respuesta.resumen.hoy.monto_colocado == 12600.13
    assert respuesta.resumen.ayer.operaciones == 3
    assert respuesta.resumen.ayer.monto_colocado == 9200
    assert respuesta.resumen.cambio.operaciones == 0
    assert respuesta.resumen.cambio.monto_colocado == 3400.13
    assert respuesta.asesores[0].hoy.operaciones == 2
    assert respuesta.asesores[0].hoy.monto_colocado == 8500.13
    assert respuesta.asesores[0].ayer.monto_colocado == 3000
    assert respuesta.asesores[0].cambio.monto_colocado == 5500.13


def test_agencia_inexistente_devuelve_404() -> None:
    service = ColocacionDiariaAsesoresService(FakeRepository(None))

    with pytest.raises(HTTPException) as error:
        service.obtener(id_agencia=88, auth_context=_auth_context())

    assert error.value.status_code == 404


def test_endpoint_expone_resumen_y_asesores_compactados() -> None:
    repository = FakeRepository(
        ColocacionDiariaData(
            id_agencia=4,
            agencia="Ambato",
            asesores=[ColocacionAsesorDia("ana", "Ana", 2, 8500, 1, 3000)],
        )
    )
    app = FastAPI()
    app.include_router(negocios_router)
    app.dependency_overrides[get_current_auth_context] = _auth_context
    app.dependency_overrides[get_colocacion_diaria_asesores_service] = lambda: (
        ColocacionDiariaAsesoresService(repository)
    )

    with TestClient(app) as client:
        response = client.get("/negocios/colocacion/diaria-asesores?id_agencia=4")

    assert response.status_code == 200
    body = response.json()
    assert body["resumen"]["hoy"]["monto_colocado"] == 8500
    assert body["resumen"]["ayer"]["monto_colocado"] == 3000
    assert body["asesores"][0]["codigo_usuario"] == "ana"
    assert body["asesores"][0]["cambio"]["monto_colocado"] == 5500

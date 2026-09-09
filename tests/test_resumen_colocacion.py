from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.colocacion.colocacion_historico.domain import (
    ColocacionAgrupada,
    DimensionesColocacion,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.colocacion.resumen.dependencies import get_resumen_colocacion_service
from app.modules.negocios.colocacion.resumen.schemas import InputResumenColocacion
from app.modules.negocios.colocacion.resumen.service import ResumenColocacionService


client = TestClient(app)


def auth_context(fecha_sistema: date = date(2026, 8, 31)) -> AuthContext:
    return AuthContext.from_token_payload(
        "token",
        UsuarioTokenPayload(
            sub="jdoe",
            usuario="John Doe",
            id_agencia=2,
            nombre_agencia="Matriz",
            fecha_sistema=fecha_sistema,
        ),
    )


def agrupacion(operaciones: int, saldo: float) -> ColocacionAgrupada:
    dimensiones = DimensionesColocacion(
        periodo="2026-08",
        anio=2026,
        mes=8,
        agencia="MATRIZ",
        condicion="NUEVO",
        tipo_prestamo="ORDINARIO",
        producto="MICROCREDITO",
        segmento="MINORISTA",
        asesor="JUAN PEREZ",
        provincia="AZUAY",
        canton="CUENCA",
        parroquia="EL VECINO",
        educacion="SUPERIOR",
        edad="HASTA 30",
        garantia="PERSONAL",
        monto="Hasta 3.000",
        tasa="Hasta 16",
        tasa_valor=16.0,
        tasa_real="Hasta 17",
        tasa_real_valor=17.0,
        plazo="Hasta 2 AÑOS",
        plazo_valor=730,
    )
    return ColocacionAgrupada(dimensiones=dimensiones, operaciones=operaciones, saldo_inicial=saldo)


class FakeColocacionHistoricoService:
    def __init__(self) -> None:
        self.llamadas: list[tuple[date, date, date, list[str]]] = []

    def obtener_agrupaciones_resumen_por_rango(self, fecha_inicio, fecha_fin, fecha_hoy, agencias):
        self.llamadas.append((fecha_inicio, fecha_fin, fecha_hoy, agencias))
        datos = {
            (date(2026, 8, 15), date(2026, 8, 25)): agrupacion(10, 1000.0),
            (date(2026, 7, 1), date(2026, 7, 31)): agrupacion(30, 3000.0),
            (date(2026, 7, 15), date(2026, 7, 25)): agrupacion(8, 800.0),
            (date(2026, 8, 1), date(2026, 8, 25)): agrupacion(20, 2000.0),
            (date(2026, 7, 1), date(2026, 7, 25)): agrupacion(15, 1500.0),
        }
        fila = datos.get((fecha_inicio, fecha_fin))
        return {fila.dimensiones: fila} if fila else {}


def test_servicio_usa_agencias_por_nombre_y_compara_el_mismo_rango_del_mes_anterior() -> None:
    historico = FakeColocacionHistoricoService()
    service = ResumenColocacionService(historico)  # type: ignore[arg-type]

    respuesta = service.obtener_resumen(
        InputResumenColocacion(
            agencias=[" MATRIZ ", "MATRIZ"],
            fecha_inicio=date(2026, 8, 15),
            fecha_fin=date(2026, 8, 25),
        ),
        auth_context(),
    )

    assert historico.llamadas == [
        (date(2026, 8, 15), date(2026, 8, 25), date(2026, 8, 31), ["MATRIZ"]),
        (date(2026, 7, 1), date(2026, 7, 31), date(2026, 8, 31), ["MATRIZ"]),
        (date(2026, 7, 15), date(2026, 7, 25), date(2026, 8, 31), ["MATRIZ"]),
    ]
    assert respuesta.fecha_inicio_periodo_anterior == date(2026, 7, 1)
    assert respuesta.fecha_fin_periodo_anterior == date(2026, 7, 31)
    assert respuesta.fecha_inicio_mismo_rango_mes_anterior == date(2026, 7, 15)
    assert respuesta.fecha_fin_mismo_rango_mes_anterior == date(2026, 7, 25)
    assert respuesta.agrupaciones[0].monto_colocado == 1000.0
    assert respuesta.agrupaciones[0].monto_colocado_periodo_anterior == 3000.0
    assert respuesta.agrupaciones[0].monto_mismo_rango_mes_anterior == 800.0
    assert respuesta.agrupaciones[0].variacion_valor == 200.0
    assert respuesta.agrupaciones[0].tasa_real == "Hasta 17"
    assert respuesta.agrupaciones[0].tasa_valor == 16.0


def test_servicio_rechaza_fecha_final_posterior_a_fecha_del_sistema() -> None:
    service = ResumenColocacionService(FakeColocacionHistoricoService())  # type: ignore[arg-type]

    with pytest.raises(HTTPException, match="fecha_fin no puede ser posterior") as error:
        service.obtener_resumen(
            InputResumenColocacion(
                agencias=["MATRIZ"],
                fecha_inicio=date(2026, 8, 1),
                fecha_fin=date(2026, 9, 1),
            ),
            auth_context(),
        )

    assert error.value.status_code == 400


def test_endpoint_devuelve_agrupaciones_dimensionales() -> None:
    service = ResumenColocacionService(FakeColocacionHistoricoService())  # type: ignore[arg-type]
    app.dependency_overrides[get_current_auth_context] = auth_context
    app.dependency_overrides[get_resumen_colocacion_service] = lambda: service
    try:
        response = client.post(
            "/negocios/colocacion/resumen",
            json={
                "agencias": ["MATRIZ"],
                "fecha_inicio": "2026-08-15",
                "fecha_fin": "2026-08-25",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["agrupaciones"][0]["asesor"] == "JUAN PEREZ"
    assert body["agrupaciones"][0]["tasa_real"] == "Hasta 17"
    assert "garantia" not in body["agrupaciones"][0]
    assert "por_producto" not in body

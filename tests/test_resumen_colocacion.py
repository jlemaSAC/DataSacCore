from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.colocacion.colocacion_historico.domain import (
    ColocacionAgrupada,
    DetalleColocacion,
    DimensionesColocacion,
    ResultadoDetalleColocacion,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.colocacion.resumen.dependencies import get_resumen_colocacion_service
from app.modules.negocios.colocacion.resumen.schemas import (
    InputDetalleResumenColocacion,
    InputResumenColocacion,
)
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
        self.llamadas_detalle: list[tuple] = []
        self.rango_tasa_real: tuple[float | None, float | None] | None = None
        self.limite_detalle: int | None = None

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

    def obtener_detalles_resumen_por_rango(
        self,
        fecha_inicio,
        fecha_fin,
        fecha_hoy,
        agencias,
        dimension,
        valor_dimension,
        asesores,
        tasa_desde=None,
        tasa_hasta_exclusiva=None,
        limite=500,
    ):
        self.llamadas_detalle.append(
            (
                fecha_inicio,
                fecha_fin,
                fecha_hoy,
                agencias,
                dimension,
                valor_dimension,
                asesores,
            )
        )
        self.rango_tasa_real = (tasa_desde, tasa_hasta_exclusiva)
        self.limite_detalle = limite
        detalles = [
            DetalleColocacion(
                numero_cliente="99014201",
                nombre_cliente="PILATAXI NAULA ELENA",
                numero_operacion="2026081703165",
                agencia="QUITO",
                asesor="ACHAFIA",
                tipo_condicion="NORMAL",
                producto="CONSUMO",
                tipo_prestamo="CREDI AGIL CONSUMO",
                segmento="MINORISTA",
                tasa_nominal=15.55,
                tasa_real=16.71,
                monto_colocado=5000.0,
            ),
            DetalleColocacion(
                numero_cliente="99035714",
                nombre_cliente="CHALUISA GUANOTUÑA VANESSA FERNANDA",
                numero_operacion="2026081703136",
                agencia="QUITO",
                asesor="ACHAFIA",
                tipo_condicion="NORMAL",
                producto="CONSUMO",
                tipo_prestamo="CREDI AGIL CONSUMO",
                segmento="MINORISTA",
                tasa_nominal=15.55,
                tasa_real=16.71,
                monto_colocado=5000.0,
            ),
        ]
        return ResultadoDetalleColocacion(
            items=detalles[:limite],
            total_registros=len(detalles),
            total_monto_colocado=sum(detalle.monto_colocado for detalle in detalles),
        )


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
    por_agencia = respuesta.agrupaciones.por_agencia[0]
    assert por_agencia.monto_colocado == 1000.0
    assert por_agencia.monto_colocado_periodo_anterior == 3000.0
    assert por_agencia.monto_mismo_rango_mes_anterior == 800.0
    assert por_agencia.variacion_valor == 200.0
    assert por_agencia.numero_operaciones == 10
    assert por_agencia.numero_operaciones_periodo_anterior == 30
    assert por_agencia.numero_operaciones_mismo_rango_mes_anterior == 8
    assert por_agencia.variacion_operaciones == 2
    assert respuesta.agrupaciones.por_tasa_normal[0].dimension == "16"
    assert respuesta.agrupaciones.por_tasa_real[0].dimension == "17% – 17.99%"
    assert respuesta.asesores_disponibles == ["JUAN PEREZ"]


def test_servicio_rechaza_fecha_final_posterior_a_fecha_del_sistema() -> None:
    service = ResumenColocacionService(FakeColocacionHistoricoService())  # type: ignore[arg-type]

    with pytest.raises(HTTPException, match="fecha_fin no puede ser posterior") as error:
        service.obtener_resumen(
                InputResumenColocacion(
                    agencias=["MATRIZ"],
                    fecha_inicio=date(2026, 9, 1),
                    fecha_fin=date(2026, 9, 2),
            ),
            auth_context(),
        )

    assert error.value.status_code == 400


@pytest.mark.parametrize("modelo", [InputResumenColocacion, InputDetalleResumenColocacion])
def test_consulta_rechaza_rango_que_cruza_de_mes(modelo) -> None:
    datos = {
        "agencias": ["MATRIZ"],
        "fecha_inicio": date(2026, 8, 31),
        "fecha_fin": date(2026, 9, 1),
    }
    if modelo is InputDetalleResumenColocacion:
        datos.update({"dimension": "agencia", "valor_dimension": "MATRIZ"})

    with pytest.raises(ValueError, match="dentro del mismo mes"):
        modelo(**datos)


def test_detalle_acepta_tasas_numericas_y_sin_datos() -> None:
    tasa_real = InputDetalleResumenColocacion(
        agencias=["MATRIZ"],
        fecha_inicio=date(2026, 8, 1),
        fecha_fin=date(2026, 8, 31),
        dimension="tasa_real",
        valor_dimension="16.71",
    )
    tasa_normal_sin_datos = InputDetalleResumenColocacion(
        agencias=["MATRIZ"],
        fecha_inicio=date(2026, 8, 1),
        fecha_fin=date(2026, 8, 31),
        dimension="tasa_normal",
        valor_dimension="SIN DATOS",
    )

    assert tasa_real.dimension == "tasa_real"
    assert tasa_normal_sin_datos.valor_dimension == "SIN DATOS"


def test_resumen_filtra_asesores_y_conserva_los_disponibles() -> None:
    service = ResumenColocacionService(FakeColocacionHistoricoService())  # type: ignore[arg-type]

    respuesta = service.obtener_resumen(
        InputResumenColocacion(
            agencias=["MATRIZ"],
            fecha_inicio=date(2026, 8, 15),
            fecha_fin=date(2026, 8, 25),
            asesores=["ASESOR INEXISTENTE"],
        ),
        auth_context(),
    )

    assert respuesta.asesores_disponibles == ["JUAN PEREZ"]
    assert respuesta.agrupaciones.por_agencia == []
    assert respuesta.agrupaciones.por_asesor == []


def test_detalle_acepta_rango_exclusivo_de_tasa_real() -> None:
    detalle = InputDetalleResumenColocacion(
        agencias=["MATRIZ"],
        fecha_inicio=date(2026, 8, 1),
        fecha_fin=date(2026, 8, 31),
        dimension="tasa_real",
        valor_dimension="4% – 4.99%",
        tasa_desde=4,
        tasa_hasta_exclusiva=5,
    )

    assert detalle.tasa_desde == 4
    assert detalle.tasa_hasta_exclusiva == 5


def test_servicio_envia_rango_de_tasa_real_al_historico() -> None:
    historico = FakeColocacionHistoricoService()
    service = ResumenColocacionService(historico)  # type: ignore[arg-type]

    service.obtener_detalle(
        InputDetalleResumenColocacion(
            agencias=["QUITO"],
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 8, 31),
            dimension="tasa_real",
            valor_dimension="4% – 4.99%",
            tasa_desde=4,
            tasa_hasta_exclusiva=5,
        ),
        auth_context(),
    )

    assert historico.rango_tasa_real == (4, 5)


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
    assert body["asesores_disponibles"] == ["JUAN PEREZ"]
    assert body["agrupaciones"]["por_asesor"][0]["dimension"] == "JUAN PEREZ"
    assert body["agrupaciones"]["por_tasa_real"][0]["dimension"] == "17% – 17.99%"
    assert body["agrupaciones"]["por_agencia"][0]["numero_operaciones"] == 10
    assert "por_producto" in body["agrupaciones"]


def test_endpoint_detalle_filtra_dimension_y_pagina() -> None:
    historico = FakeColocacionHistoricoService()
    service = ResumenColocacionService(historico)  # type: ignore[arg-type]
    app.dependency_overrides[get_current_auth_context] = auth_context
    app.dependency_overrides[get_resumen_colocacion_service] = lambda: service
    try:
        response = client.post(
            "/negocios/colocacion/resumen/detalle",
            json={
                "agencias": ["QUITO"],
                "fecha_inicio": "2026-08-01",
                "fecha_fin": "2026-08-31",
                "dimension": "tipo_prestamo",
                "valor_dimension": "CREDI AGIL CONSUMO",
                "asesores": ["ACHAFIA"],
                "pagina": 2,
                "tamano_pagina": 1,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert historico.llamadas_detalle == [
        (
            date(2026, 8, 1),
            date(2026, 8, 31),
            date(2026, 8, 31),
            ["QUITO"],
            "tipo_prestamo",
            "CREDI AGIL CONSUMO",
            ["ACHAFIA"],
        )
    ]
    body = response.json()
    assert body["total_registros"] == 2
    assert body["total_monto_colocado"] == 10000.0
    assert historico.limite_detalle == 2
    assert body["items"] == [
        {
            "numero_cliente": "99035714",
            "nombre_cliente": "CHALUISA GUANOTUÑA VANESSA FERNANDA",
            "numero_operacion": "2026081703136",
            "agencia": "QUITO",
            "asesor": "ACHAFIA",
            "tipo_condicion": "NORMAL",
            "producto": "CONSUMO",
            "tipo_prestamo": "CREDI AGIL CONSUMO",
            "segmento": "MINORISTA",
            "tasa_nominal": 15.55,
            "tasa_real": 16.71,
            "monto_colocado": 5000.0,
        }
    ]

from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.inversiones.schemas import ReporteInversionesFila
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.inversiones.depositos_a_plazo.dependencies import get_resumen_actual_depositos_service
from app.modules.negocios.inversiones.depositos_a_plazo.schemas import InputResumenActualDepositos
from app.modules.negocios.inversiones.depositos_a_plazo.service import ResumenActualDepositosService


def auth():
    return AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="Test", id_agencia=1, nombre_agencia="MATRIZ",
        fecha_sistema=date(2026, 9, 18),
    ))


def fila(fecha, *, agencia="MATRIZ", creacion="2026-09-02", tasa=8, operaciones=1, saldo=100, condicion="NUEVO"):
    return ReporteInversionesFila(
        fecha_corte=fecha, fecha_creacion=creacion, periodo=f"{fecha[:4]}-{fecha[4:6]}",
        anio=int(fecha[:4]), mes=int(fecha[4:6]), agencia=agencia, asesor="ASESOR",
        periodicidad_pago="MENSUAL", tipo_pago="PERIODICO", condicion=condicion,
        periodo_plazo="DE 31 A 90", estado="ACTIVO", provincia="", canton="", parroquia="",
        tiene_prestamo=False, tasa_efectiva=tasa, tasa_entera=int(tasa), tasa_decimal=tasa,
        operaciones=operaciones, saldo=saldo,
    )


class Fuente:
    def __init__(self, filas):
        self.filas = filas
        self.solicitudes = []

    def obtener_corte_actual(self, fecha):
        self.solicitudes.append(fecha)
        return [f.model_dump() for f in self.filas.get(fecha, [])]

    def obtener_por_rango(self, desde, hasta, contexto):
        assert desde == hasta
        self.solicitudes.append(desde)
        return SimpleNamespace(filas=self.filas.get(desde, []))


def servicio():
    fuente = Fuente({
        date(2026, 9, 18): [
            fila("20260918", tasa=10, operaciones=3, saldo=900),
            fila("20260918", tasa=6, creacion="2026-08-01", saldo=200),
            fila("20260918", tasa=8, condicion="RENOVADO", saldo=100),
            fila("20260918", agencia="CUENCA", tasa=4, saldo=50),
        ],
        date(2026, 8, 31): [fila("20260828", tasa=5, saldo=500)],
        date(2025, 12, 31): [fila("20251231", tasa=3, saldo=300)],
    })
    return ResumenActualDepositosService(fuente, fuente), fuente


def test_promedios_por_operacion_y_renovacion_incluye_nuevos_y_renovados():
    service, fuente = servicio()
    respuesta = service.obtener_resumen(InputResumenActualDepositos(fecha_inicio="2026-09-01", fecha_fin="2026-09-18"), auth())
    assert respuesta.actual.saldo == 1250
    assert respuesta.actual.numero_operaciones == 6
    assert respuesta.actual.tasa_promedio == 8
    assert respuesta.actual.tasa_promedio_renovacion == 8.4  # (3*10 + 8 + 4) / 5
    assert respuesta.mes_anterior.fecha_corte == date(2026, 8, 28)
    assert respuesta.anio_anterior.saldo == 300
    assert fuente.solicitudes == [date(2026, 9, 18), date(2026, 8, 31), date(2025, 12, 31)]
    assert sum(a.saldo for a in respuesta.por_agencia) == respuesta.actual.saldo


def test_filtra_agencias_y_tasas_no_son_promedios_de_promedios():
    service, _ = servicio()
    respuesta = service.obtener_resumen(InputResumenActualDepositos(
        fecha_inicio="2026-09-01", fecha_fin="2026-09-18", agencias=[" matriz ", "MATRIZ"],
    ), auth())
    assert respuesta.agencias == ["MATRIZ"]
    assert not respuesta.consolidado
    assert respuesta.actual.saldo == 1200
    assert respuesta.actual.tasa_promedio == 8.8
    assert respuesta.actual.tasa_promedio_renovacion == 9.5
    assert [a.agencia for a in respuesta.por_agencia] == ["MATRIZ"]


def test_no_hay_ingresos_o_comparativos_no_inventa_tasas():
    fuente = Fuente({date(2026, 9, 18): [fila("20260918", creacion="2026-08-01")]})
    respuesta = ResumenActualDepositosService(fuente, fuente).obtener_resumen(
        InputResumenActualDepositos(fecha_inicio="2026-09-01", fecha_fin="2026-09-18"), auth(),
    )
    assert respuesta.actual.tasa_promedio_renovacion is None
    assert respuesta.mes_anterior is None
    assert respuesta.anio_anterior is None


def test_detalle_agencia_contiene_indicadores_actuales():
    service, _ = servicio()
    respuesta = service.obtener_resumen(InputResumenActualDepositos(
        fecha_inicio="2026-09-01", fecha_fin="2026-09-18", agencias=["CUENCA"],
    ), auth())
    assert respuesta.por_agencia[0].saldo == 50
    assert respuesta.por_agencia[0].numero_operaciones == 1


def test_corte_intramensual_historico_no_se_sustituye_por_cierre_mensual():
    fuente = Fuente({date(2026, 8, 12): [fila("20260812")]})
    respuesta = ResumenActualDepositosService(fuente, fuente).obtener_resumen(
        InputResumenActualDepositos(fecha_inicio="2026-08-01", fecha_fin="2026-08-12"), auth(),
    )
    assert respuesta.actual.fecha_corte == date(2026, 8, 12)
    assert fuente.solicitudes[0] == date(2026, 8, 12)


def test_enero_consulta_una_sola_vez_el_cierre_compartido():
    fuente = Fuente({})
    ResumenActualDepositosService(fuente, fuente).obtener_resumen(
        InputResumenActualDepositos(fecha_inicio="2026-01-01", fecha_fin="2026-01-10"), auth(),
    )
    assert fuente.solicitudes == [date(2026, 1, 10), date(2025, 12, 31)]


def test_fecha_futura_rechazada_antes_de_consultar_fuentes():
    service, fuente = servicio()
    with pytest.raises(HTTPException) as exc:
        service.obtener_resumen(InputResumenActualDepositos(fecha_inicio="2026-09-01", fecha_fin="2026-09-19"), auth())
    assert exc.value.status_code == 400
    assert fuente.solicitudes == []


def test_endpoint_autenticado_y_validacion():
    service, _ = servicio()
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_resumen_actual_depositos_service] = lambda: service
    try:
        client = TestClient(app)
        url = "/negocios/inversiones/depositos-a-plazo/resumen-actual"
        respuesta = client.post(url, json={"fecha_inicio": "2026-09-01", "fecha_fin": "2026-09-18", "agencias": []})
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["actual"]["saldo"] == 1250
        assert datos["fecha_inicio"] == "2026-09-01"
        assert datos["fecha_fin"] == "2026-09-18"
        assert set(datos["por_agencia"][0]) == {
            "agencia", "saldo", "numero_operaciones", "tasa_promedio", "tasa_promedio_renovacion"
        }
        assert datos["mes_anterior"] is not None
        assert datos["anio_anterior"] is not None
        assert client.post(url, json={"fecha_inicio": "2026-09-01", "fecha_fin": "2026-09-18", "agencias": [""]}).status_code == 422
        assert client.post(url, json={"fecha_inicio": "2026-02-01", "fecha_fin": "2026-02-30"}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_endpoint_requiere_bearer():
    assert TestClient(app).post(
        "/negocios/inversiones/depositos-a-plazo/resumen-actual",
        json={"fecha_inicio": "2026-09-01", "fecha_fin": "2026-09-18"},
    ).status_code == 401


def test_fecha_inicio_limita_tasa_de_ingresos_sin_reducir_saldo_del_corte():
    fuente = Fuente({date(2026, 9, 18): [
        fila("20260918", creacion="2026-09-02", tasa=10, saldo=900),
        fila("20260918", creacion="2026-09-12", tasa=6, saldo=100),
    ]})
    respuesta = ResumenActualDepositosService(fuente, fuente).obtener_resumen(
        InputResumenActualDepositos(fecha_inicio="2026-09-10", fecha_fin="2026-09-18"), auth(),
    )
    assert respuesta.actual.saldo == 1000
    assert respuesta.actual.tasa_promedio == 8
    assert respuesta.actual.tasa_promedio_renovacion == 6
    assert respuesta.por_agencia[0].tasa_promedio_renovacion == 6


@pytest.mark.parametrize("inicio,fin", [("2026-09-18", "2026-09-01"), ("2026-08-01", "2026-09-18")])
def test_valida_rango_del_request(inicio, fin):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        InputResumenActualDepositos(fecha_inicio=inicio, fecha_fin=fin)

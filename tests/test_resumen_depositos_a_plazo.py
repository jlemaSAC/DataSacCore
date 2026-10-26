from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.inversiones.schemas import ReporteInversionesFila
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.depositos_a_plazos.resumen_depositos_a_plazo.dependencies import (
    get_resumen_depositos_a_plazo_service,
)
from app.modules.negocios.depositos_a_plazos.resumen_depositos_a_plazo.service import (
    ResumenDepositosAPlazoService,
)
from app.modules.negocios.inversiones.depositos_a_plazo.schemas import InputResumenActualDepositos
from app.modules.negocios.inversiones.depositos_a_plazo.service import ResumenActualDepositosService

URL = "/negocios/depositos-a-plazos/resumen-depositos-a-plazo"


def auth():
    return AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="Test", id_agencia=1, nombre_agencia="MATRIZ",
        fecha_sistema=date(2026, 9, 18),
    ))


def fila(**cambios):
    valores = dict(
        fecha_corte="20260918", fecha_creacion="2026-09-02", periodo="2026-09",
        anio=2026, mes=9, agencia="MATRIZ", asesor="ANA", periodicidad_pago="MENSUAL",
        tipo_pago="PERIODICO", condicion="NUEVO", periodo_plazo="DE 31 A 90",
        estado="ACTIVO", provincia="", canton="", parroquia="", tiene_prestamo=False,
        tasa_efectiva=10, tasa_variacion=0.5, tasa_entera=10, tasa_decimal=10,
        operaciones=3, saldo=900,
    )
    return ReporteInversionesFila(**(valores | cambios))


class Fuente:
    def __init__(self, filas):
        self.filas = filas
        self.solicitudes = []

    def obtener_corte_actual(self, fecha):
        self.solicitudes.append(fecha)
        return [f.model_dump() for f in self.filas]

    def obtener_por_rango(self, desde, hasta, contexto):
        self.solicitudes.append(desde)
        return SimpleNamespace(filas=[])


def servicio(filas=None):
    fuente = Fuente(filas if filas is not None else [
        fila(),
        fila(asesor="LUIS", periodicidad_pago="AL VENCIMIENTO", condicion="RENOVADO",
             tasa_efectiva=6, operaciones=1, saldo=100),
        fila(fecha_creacion="2026-08-01", condicion="VIGENTE NUEVO",
             tasa_efectiva=8, operaciones=1, saldo=200),
        fila(agencia="CUENCA", asesor="ANA", fecha_creacion="2026-09-12",
             tasa_efectiva=4, operaciones=1, saldo=50),
    ])
    return ResumenDepositosAPlazoService(ResumenActualDepositosService(fuente, fuente)), fuente


def request(**cambios):
    return InputResumenActualDepositos(**{
        "fecha_inicio": "2026-09-01", "fecha_fin": "2026-09-18", **cambios,
    })


def test_dimensiones_reconcilian_saldo_operaciones_y_tasas_ponderadas():
    service, fuente = servicio()
    resultado = service.obtener_resumen(request(), auth())
    assert resultado.actual.saldo == 1250
    assert resultado.actual.tasa_promedio == 8
    for grupos in (resultado.por_agencia, resultado.por_asesor,
                   resultado.por_periodicidad, resultado.por_condicion):
        assert sum(f.saldo for f in grupos) == 1250
        assert sum(f.numero_operaciones for f in grupos) == 6
    ana = next(f for f in resultado.por_asesor if f.asesor == "ANA")
    assert ana.tasa_promedio == 8.4  # (3*10 + 8 + 4) / 5; no duplica tasa_variacion.
    assert ana.tasa_promedio_renovacion == 8.5
    assert fuente.solicitudes == [date(2026, 9, 18), date(2026, 8, 31), date(2025, 12, 31)]


def test_diario_por_creacion_y_condicion_incluye_dias_cero_sin_arrastrar_saldo_vigente():
    service, _ = servicio()
    resultado = service.obtener_resumen(request(), auth())
    assert len(resultado.diario) == 18
    assert resultado.diario[0].monto_total == 0
    assert resultado.diario[1].monto_por_condicion == {"NUEVO": 900, "RENOVADO": 100}
    assert resultado.diario[1].numero_operaciones == 4
    assert resultado.diario[11].monto_total == 50
    assert sum(d.monto_total for d in resultado.diario) == 1050
    assert all(sum(d.monto_por_condicion.values()) == d.monto_total for d in resultado.diario)


def test_agencia_y_fecha_inicio_se_aplican_a_todas_las_vistas():
    service, _ = servicio()
    resultado = service.obtener_resumen(request(fecha_inicio="2026-09-10", agencias=[" matriz "]), auth())
    assert resultado.actual.saldo == 1200
    assert len(resultado.diario) == 9
    assert all(d.monto_total == 0 for d in resultado.diario)
    assert all(f.tasa_promedio_renovacion is None for f in resultado.por_asesor)
    assert {f.asesor for f in resultado.por_asesor} == {"ANA", "LUIS"}


def test_solo_usa_el_ultimo_corte_disponible_y_no_repite_el_diario():
    service, _ = servicio([
        fila(fecha_corte="20260917", saldo=800),
        fila(fecha_corte="20260918", saldo=900),
        fila(fecha_corte="20260919", saldo=1000),
    ])
    resultado = service.obtener_resumen(request(), auth())
    assert resultado.actual.saldo == 900
    assert resultado.diario[1].monto_total == 900


def test_vacio_y_sin_fecha_creacion_no_inventa_ingresos():
    service, _ = servicio([])
    resultado = service.obtener_resumen(request(), auth())
    assert resultado.actual is None
    assert resultado.por_asesor == []
    assert len(resultado.diario) == 18
    service, _ = servicio([fila(fecha_creacion=None, asesor=" ")])
    resultado = service.obtener_resumen(request(), auth())
    assert resultado.por_asesor[0].asesor == "SIN DATOS"
    assert sum(d.monto_total for d in resultado.diario) == 0


def test_fecha_futura_se_rechaza_antes_de_consultar():
    service, fuente = servicio()
    with pytest.raises(HTTPException) as error:
        service.obtener_resumen(request(fecha_fin="2026-09-19"), auth())
    assert error.value.status_code == 400
    assert fuente.solicitudes == []


def test_endpoint_contrato_y_validacion():
    service, _ = servicio()
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_resumen_depositos_a_plazo_service] = lambda: service
    try:
        client = TestClient(app)
        response = client.post(URL, json=request().model_dump(mode="json"))
        assert response.status_code == 200
        assert response.json()["diario"][1]["monto_por_condicion"] == {"NUEVO": 900, "RENOVADO": 100}
        for clave in ("por_agencia", "por_asesor", "por_periodicidad", "por_condicion"):
            assert response.json()[clave]
        for body in (
            {"fecha_inicio": "2026-08-01", "fecha_fin": "2026-09-18"},
            {"fecha_inicio": "2026-09-18", "fecha_fin": "2026-09-01"},
            {"fecha_inicio": "2026-09-01", "fecha_fin": "2026-09-18", "agencias": [""]},
        ):
            assert client.post(URL, json=body).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_endpoint_requiere_bearer():
    assert TestClient(app).post(URL, json=request().model_dump(mode="json")).status_code == 401

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from bson.decimal128 import Decimal128
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.recuperacion.resumen_recuperacion.dependencies import get_resumen_recuperacion_service
from app.modules.negocios.recuperacion.resumen_recuperacion.domain import RecuperacionDiaria
from app.modules.negocios.recuperacion.resumen_recuperacion.repositories.mongo_resumen_recuperacion_repository import MongoResumenRecuperacionRepository
from app.modules.negocios.recuperacion.resumen_recuperacion.schemas import InputResumenRecuperacion
from app.modules.negocios.recuperacion.resumen_recuperacion.service import ResumenRecuperacionService


def contexto(hoy=date(2026, 10, 3)):
    return AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="Test", id_agencia=2, nombre_agencia="Matriz", fecha_sistema=hoy,
    ))


class FakeRepository:
    def __init__(self, filas=()):
        self.filas = list(filas)
        self.llamadas = []

    def obtener_diario(self, rangos, hoy, agencias):
        self.llamadas.append((rangos, hoy, agencias))
        return self.filas


def test_diario_comparativos_y_composicion_comparten_los_mismos_importes():
    repo = FakeRepository([
        RecuperacionDiaria(date(2026, 10, 1), {"CAPITAL": Decimal("100.10"), "INTERES": Decimal("20.20")}),
        RecuperacionDiaria(date(2026, 10, 3), {"CAPITAL": Decimal("50.30"), "INTERES_MORA": Decimal("-1.10")}),
        RecuperacionDiaria(date(2026, 9, 1), {"CAPITAL": Decimal("40")}),
        RecuperacionDiaria(date(2026, 9, 4), {"CAPITAL": Decimal("999")}),
        RecuperacionDiaria(date(2025, 10, 1), {"INTERES": Decimal("10")}),
    ])
    respuesta = ResumenRecuperacionService(repo).obtener_resumen(
        InputResumenRecuperacion(fecha_inicio="2026-10-01", fecha_fin="2026-10-03", agencias=[" matriz ", "MATRIZ"]), contexto(),
    )
    assert len(repo.llamadas) == 1
    assert respuesta.agencias == ["MATRIZ"]
    assert not respuesta.consolidado
    assert respuesta.actual.recuperacion_total == 169.50
    assert sum(d.recuperacion_total for d in respuesta.diario) == pytest.approx(respuesta.actual.recuperacion_total)
    for tipo, monto in respuesta.actual.recuperacion_por_tipo.items():
        assert sum(d.recuperacion_por_tipo[tipo] for d in respuesta.diario) == pytest.approx(monto)
    assert respuesta.diario[1].fecha == date(2026, 10, 2)
    assert respuesta.diario[1].recuperacion_total == 0
    assert respuesta.mes_anterior.recuperacion_total == 1039
    assert respuesta.anio_anterior.recuperacion_total == 10
    assert respuesta.mes_anterior.fecha_inicio == date(2026, 9, 1)
    assert respuesta.mes_anterior.fecha_fin == date(2026, 9, 30)
    assert respuesta.anio_anterior.fecha_inicio == date(2025, 1, 1)
    assert respuesta.anio_anterior.fecha_fin == date(2025, 12, 31)


@pytest.mark.parametrize("inicio,fin,mes_inicio,mes_fin,anio_fin", [
    ("2026-03-29", "2026-03-31", date(2026, 2, 1), date(2026, 2, 28), date(2025, 12, 31)),
    ("2024-03-29", "2024-03-31", date(2024, 2, 1), date(2024, 2, 29), date(2023, 12, 31)),
    ("2025-02-28", "2025-02-28", date(2025, 1, 1), date(2025, 1, 31), date(2024, 12, 31)),
    ("2026-01-01", "2026-01-03", date(2025, 12, 1), date(2025, 12, 31), date(2025, 12, 31)),
])
def test_periodos_completos_en_meses_cortos_bisiestos_y_cambio_de_anio(inicio, fin, mes_inicio, mes_fin, anio_fin):
    respuesta = ResumenRecuperacionService(FakeRepository()).obtener_resumen(
        InputResumenRecuperacion(fecha_inicio=inicio, fecha_fin=fin), contexto(),
    )
    assert respuesta.consolidado
    assert respuesta.mes_anterior.fecha_inicio == mes_inicio
    assert respuesta.mes_anterior.fecha_fin == mes_fin
    assert respuesta.anio_anterior.fecha_inicio == date(anio_fin.year, 1, 1)
    assert respuesta.anio_anterior.fecha_fin == anio_fin
    assert all(d.recuperacion_total == 0 for d in respuesta.diario)


def test_futuro_se_rechaza_sin_consultar_la_base():
    repo = FakeRepository()
    with pytest.raises(HTTPException) as exc:
        ResumenRecuperacionService(repo).obtener_resumen(
            InputResumenRecuperacion(fecha_inicio="2026-10-01", fecha_fin="2026-10-04"), contexto(),
        )
    assert exc.value.status_code == 400
    assert repo.llamadas == []


@pytest.mark.parametrize("datos", [
    {"fecha_inicio": "2026-09-30", "fecha_fin": "2026-10-01"},
    {"fecha_inicio": "2026-10-03", "fecha_fin": "2026-10-01"},
    {"fecha_inicio": "2026-10-01", "fecha_fin": "2026-10-03", "agencias": [" "]},
])
def test_contrato_rechaza_filtros_invalidos(datos):
    with pytest.raises(ValidationError):
        InputResumenRecuperacion(**datos)


class FakeCollection:
    def __init__(self, filas):
        self.filas = filas
        self.llamadas = []

    def aggregate(self, pipeline, **opciones):
        self.llamadas.append((pipeline, opciones))
        return iter(self.filas)


def repositorio_con_filas():
    historico = FakeCollection([{"_id": "20261001", "CAPITAL": Decimal128("12.34")}])
    actual = FakeCollection([{"_id": "20261003", "INTERES": Decimal128("1.20")}])
    colecciones = {"RecuperacionCrediticia": historico, "RecuperacionCrediticiaActual": actual}
    return MongoResumenRecuperacionRepository(colecciones), historico, actual


def test_repositorio_usa_dos_consultas_selectivas_sin_duplicar_hoy():
    repo, historico, actual = repositorio_con_filas()
    filas = repo.obtener_diario([
        (date(2026, 10, 1), date(2026, 10, 3)),
        (date(2026, 9, 1), date(2026, 9, 30)),
        (date(2025, 1, 1), date(2025, 12, 31)),
    ], date(2026, 10, 3), ["MATRIZ"])
    assert len(historico.llamadas) == len(actual.llamadas) == 1
    assert filas[0].montos["CAPITAL"] == Decimal("12.34")
    assert filas[1].montos["INTERES"] == Decimal("1.20")
    rangos = historico.llamadas[0][0][0]["$match"]["$or"]
    assert rangos[-1]["fecha_corte"]["$lte"] == "20261002"
    assert rangos == [
        {"fecha_corte": {"$gte": "20250101", "$lte": "20251231"}},
        {"fecha_corte": {"$gte": "20260901", "$lte": "20261002"}},
    ]  # Se consultan únicamente los períodos solicitados, sin los meses intermedios.
    assert actual.llamadas[0][0][0]["$match"] == {"fecha_corte": {"$gte": "20261003", "$lte": "20261003"}}
    for collection in (historico, actual):
        pipeline = collection.llamadas[0][0]
        assert not any("$lookup" in etapa or "$unwind" in etapa for etapa in pipeline)


def test_rango_cerrado_no_consulta_coleccion_actual_y_funde_intervalos_solapados():
    repo, historico, actual = repositorio_con_filas()
    repo.obtener_diario([(date(2026, 9, 1), date(2026, 9, 3)), (date(2026, 9, 2), date(2026, 9, 4))], date(2026, 10, 3), [])
    assert actual.llamadas == []
    assert historico.llamadas[0][0][0]["$match"] == {"fecha_corte": {"$gte": "20260901", "$lte": "20260904"}}


def test_enero_consulta_diciembre_una_sola_vez_dentro_del_anio_anterior():
    repo, historico, actual = repositorio_con_filas()
    repo.obtener_diario([
        (date(2026, 1, 1), date(2026, 1, 3)),
        (date(2025, 12, 1), date(2025, 12, 31)),
        (date(2025, 1, 1), date(2025, 12, 31)),
    ], date(2026, 10, 3), [])
    assert actual.llamadas == []
    assert len(historico.llamadas) == 1
    assert historico.llamadas[0][0][0]["$match"] == {
        "fecha_corte": {"$gte": "20250101", "$lte": "20260103"}
    }


def test_error_del_repositorio_devuelve_error_controlado():
    def fallar(*args):
        raise RuntimeError("Error interno de conexión")
    with pytest.raises(HTTPException) as exc:
        ResumenRecuperacionService(SimpleNamespace(obtener_diario=fallar)).obtener_resumen(
            InputResumenRecuperacion(fecha_inicio="2026-10-01", fecha_fin="2026-10-03"), contexto(),
        )
    assert exc.value.status_code == 500
    assert "conexión" not in exc.value.detail


def test_endpoint_con_bearer_devuelve_resumen_y_diario():
    originales = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_auth_context] = contexto
    app.dependency_overrides[get_resumen_recuperacion_service] = lambda: ResumenRecuperacionService(FakeRepository())
    try:
        client = TestClient(app)
        response = client.post("/negocios/recuperacion/resumen", json={"fecha_inicio": "2026-10-01", "fecha_fin": "2026-10-03"}, headers={"Authorization": "Bearer token"})
        assert response.status_code == 200
        assert len(response.json()["diario"]) == 3
        assert response.json()["anio_anterior"]["fecha_inicio"] == "2025-01-01"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(originales)


@pytest.mark.parametrize("ruta", ["resumen", "resumen-actual"])
def test_endpoint_requiere_autenticacion(ruta):
    client = TestClient(app)
    response = client.post(f"/negocios/recuperacion/{ruta}", json={"fecha_inicio": "2026-10-01", "fecha_fin": "2026-10-03"})
    assert response.status_code in (401, 403)


@pytest.mark.parametrize("agencias", [[], [" matriz ", "MATRIZ"]])
@pytest.mark.parametrize("inicio,fin,mes_inicio,mes_fin", [
    (date(2026, 8, 15), date(2026, 8, 25), date(2026, 7, 1), date(2026, 7, 31)),
    (date(2026, 10, 1), date(2026, 10, 3), date(2026, 9, 1), date(2026, 9, 30)),
])
def test_endpoints_comparten_comparativos_con_mes_y_anio_completos(
    inicio, fin, mes_inicio, mes_fin, agencias,
):
    repo = FakeRepository([
        RecuperacionDiaria(inicio, {"CAPITAL": Decimal("600")}),
        RecuperacionDiaria(fin, {"INTERES": Decimal("400")}),
        RecuperacionDiaria(mes_inicio, {"CAPITAL": Decimal("1000")}),
        RecuperacionDiaria(mes_fin, {"INTERES": Decimal("2000")}),
        RecuperacionDiaria(date(2025, 1, 1), {"CAPITAL": Decimal("1500")}),
        RecuperacionDiaria(date(2025, 12, 31), {"INTERES": Decimal("2500")}),
        RecuperacionDiaria(date(2024, 12, 31), {"CAPITAL": Decimal("999")}),
    ])
    originales = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_auth_context] = contexto
    app.dependency_overrides[get_resumen_recuperacion_service] = lambda: ResumenRecuperacionService(repo)
    try:
        client = TestClient(app)
        payload = {"fecha_inicio": inicio.isoformat(), "fecha_fin": fin.isoformat(), "agencias": agencias}
        respuestas = [
            client.post(f"/negocios/recuperacion/{ruta}", json=payload, headers={"Authorization": "Bearer token"})
            for ruta in ("resumen-actual", "resumen")
        ]
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(originales)

    assert all(respuesta.status_code == 200 for respuesta in respuestas)
    actual, resumen = [respuesta.json() for respuesta in respuestas]
    assert "diario" not in actual
    assert actual == {clave: valor for clave, valor in resumen.items() if clave != "diario"}
    assert actual["agencias"] == (["MATRIZ"] if agencias else [])
    assert actual["consolidado"] is (not agencias)
    assert actual["actual"]["recuperacion_total"] == 1000
    assert actual["mes_anterior"]["fecha_inicio"] == mes_inicio.isoformat()
    assert actual["mes_anterior"]["fecha_fin"] == mes_fin.isoformat()
    assert actual["mes_anterior"]["recuperacion_total"] == 3000
    assert actual["anio_anterior"]["fecha_inicio"] == "2025-01-01"
    assert actual["anio_anterior"]["fecha_fin"] == "2025-12-31"
    assert actual["anio_anterior"]["recuperacion_total"] == 4000
    assert len(resumen["diario"]) == (fin - inicio).days + 1
    assert sum(dia["recuperacion_total"] for dia in resumen["diario"]) == 1000
    assert repo.llamadas == [
        ([(inicio, fin), (mes_inicio, mes_fin), (date(2025, 1, 1), date(2025, 12, 31))], date(2026, 10, 3), ["MATRIZ"] if agencias else [])
    ] * 2

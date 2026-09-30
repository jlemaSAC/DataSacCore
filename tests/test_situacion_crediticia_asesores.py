from datetime import datetime

import pytest
from fastapi import HTTPException

from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.service import (
    SituacionCrediticiaAsesoresService,
    _obtener_reasignaciones,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.mongo_situacion_crediticia_asesores_repository import (
    MongoSituacionCrediticiaAsesoresRepository,
)


def _document(
    numero: str,
    codigo: str,
    *,
    nombre: str,
    cliente: int,
    agencia: str = "CENTRO",
    saldo: float = 100.0,
    no_devenga: float = 10.0,
    vencido: float = 5.0,
    provision: float = 2.0,
    provision_calculada: float | None = None,
    diferido: bool = False,
) -> dict:
    document = {
        "NumeroPrestamo": numero,
        "CodigoUsuario": codigo,
        "NombreAsesor": nombre,
        "CargoAsesor": "ASESOR DE NEGOCIOS",
        "Agencia": agencia,
        "Cliente": cliente,
        "SaldoCapital": saldo,
        "CapitalNoDevenga": no_devenga,
        "CapitalVencido": vencido,
        "ProvisionRequerida": provision,
        "EstadoPrestamo": "VIGENTE",
        "EsDiferido": diferido,
    }
    if provision_calculada is not None:
        document["ProvisionRequeridaCalculada"] = provision_calculada
    return document


class FakeMongoRepository:
    def __init__(
        self,
        actuales: list[dict],
        historicos: list[dict],
        cierres_mes_anterior: list[dict] | None = None,
    ) -> None:
        self.actuales = actuales
        self.historicos = historicos
        self.cierres_mes_anterior = cierres_mes_anterior or historicos

    def obtener_ultimo_corte_actual(self) -> str:
        return "20260923"

    def obtener_actual(self, fecha_corte: str, agencia_nombre: str | None) -> list[dict]:
        assert fecha_corte == "20260923"
        assert agencia_nombre is None
        return self.actuales

    def obtener_historico(self, fecha_corte: str, agencia_nombre: str | None) -> list[dict]:
        assert fecha_corte == "20260831"
        assert agencia_nombre is None
        return self.cierres_mes_anterior


class FakeSqlRepository:
    def obtener_nombre_agencia(self, id_agencia: int) -> str | None:
        raise AssertionError("No debe consultar SQL para el consolidado")

    def obtener_gerentes_oficina(self, agencias: list[str]) -> list[dict]:
        assert agencias == ["CENTRO"]
        return []


def test_reasignacion_se_infiere_por_numero_de_prestamo() -> None:
    historicos = [_document("1", "ASESOR_ANTERIOR", nombre="Anterior", cliente=1)]
    actuales = [_document("1", "ASESOR_ACTUAL", nombre="Actual", cliente=1)]

    assert _obtener_reasignaciones(actuales, historicos) == {
        "1": "ASESOR_ACTUAL"
    }


def test_service_usa_actual_para_el_lado_vigente_y_reasigna_historico() -> None:
    historicos = [
        _document("1", "ASESOR_ANTERIOR", nombre="Anterior", cliente=1),
        _document("2", "ASESOR_ACTUAL", nombre="Actual", cliente=2),
    ]
    actuales = [
        _document("1", "ASESOR_ACTUAL", nombre="Actual", cliente=1),
        _document("2", "ASESOR_ACTUAL", nombre="Actual", cliente=2),
    ]
    service = SituacionCrediticiaAsesoresService(
        FakeMongoRepository(actuales, historicos),
        FakeSqlRepository(),
    )

    response = service.obtener(
        fecha_inicio=datetime(2026, 9, 1).date(),
        fecha_fin=datetime(2026, 9, 23).date(),
        ahora=datetime(2026, 9, 23),
    )

    assert response.fecha_corte_actual == "20260923"
    assert response.fecha_corte_cierre_mes_anterior == "20260831"
    assert len(response.comparacion) == 1
    item = response.comparacion[0]
    assert item.codigo_usuario == "ASESOR_ACTUAL"
    assert item.nombre_asesor_actual == "Actual"
    assert item.nombre_asesor_cierre_mes_anterior == "Anterior"
    assert item.valores_actual is not None
    assert item.valores_actual.operaciones == 2
    assert item.valores_cierre_mes_anterior is not None
    assert item.valores_cierre_mes_anterior.operaciones == 2
    assert item.diferencias_cierre_mes_anterior is not None
    assert response.faltantes_en_cierre_mes_anterior == []
    assert response.faltantes_en_actual == []


def test_service_filtra_diferidos_en_ambos_snapshots() -> None:
    historicos = [
        _document("1", "ASESOR", nombre="Asesor", cliente=1),
        _document("2", "ASESOR", nombre="Asesor", cliente=2, diferido=True),
    ]
    actuales = [
        _document("1", "ASESOR", nombre="Asesor", cliente=1),
        _document("2", "ASESOR", nombre="Asesor", cliente=2, diferido=True),
    ]
    service = SituacionCrediticiaAsesoresService(
        FakeMongoRepository(actuales, historicos),
        FakeSqlRepository(),
    )

    response = service.obtener(
        fecha_inicio=datetime(2026, 9, 1).date(),
        fecha_fin=datetime(2026, 9, 23).date(),
        filtrar_diferidos=False,
        ahora=datetime(2026, 9, 23),
    )

    item = response.comparacion[0]
    assert item.valores_actual is not None
    assert item.valores_actual.operaciones == 1
    assert item.valores_cierre_mes_anterior is not None
    assert item.valores_cierre_mes_anterior.operaciones == 1


def test_provision_actual_y_historica_siguen_reglas_de_resumen_actual() -> None:
    actuales = [
        _document(
            "1",
            "ASESOR",
            nombre="Asesor",
            cliente=1,
            provision=10,
            provision_calculada=99,
        )
    ]
    cierres_mes_anterior = [
        _document(
            "1",
            "ASESOR",
            nombre="Asesor",
            cliente=1,
            provision=5,
            provision_calculada=20,
        )
    ]
    service = SituacionCrediticiaAsesoresService(
        FakeMongoRepository(actuales, cierres_mes_anterior),
        FakeSqlRepository(),
    )

    response = service.obtener(
        fecha_inicio=datetime(2026, 9, 1).date(),
        fecha_fin=datetime(2026, 9, 23).date(),
        ahora=datetime(2026, 9, 23),
    )

    item = response.comparacion[0]
    assert item.valores_actual is not None
    assert item.valores_cierre_mes_anterior is not None
    assert item.valores_actual.provision_requerida == 10
    assert item.valores_cierre_mes_anterior.provision_requerida == 20


class _FakeCollection:
    def __init__(self) -> None:
        self.last_find_filter = None

    def find_one(self, filtro, projection, sort=None):
        if sort:
            return {"as_of": "20260923T151800"}
        return None

    def find(self, filtro, projection):
        self.last_find_filter = filtro
        return iter(
            [
                {
                    "CodigoAsesor": "ASESOR",
                    "NombreAsesor": "Asesor Actual",
                    "Agencia": "CENTRO",
                }
            ]
        )


class _FakeDatabase:
    def __init__(self) -> None:
        self.collections = {
            "SituacionCrediticiaActual": _FakeCollection(),
            "SituacionCrediticia": _FakeCollection(),
        }

    def __getitem__(self, name):
        return self.collections[name]


def test_actual_no_filtra_por_fecha_corte_inexistente() -> None:
    database = _FakeDatabase()
    repository = MongoSituacionCrediticiaAsesoresRepository(database)

    actuales = repository.obtener_actual("20260923")

    assert len(actuales) == 1
    assert database.collections["SituacionCrediticiaActual"].last_find_filter == {
        "EstadoPrestamo": {"$ne": "CANCELADO"}
    }


def test_service_rechaza_rango_de_meses_diferentes() -> None:
    service = SituacionCrediticiaAsesoresService(
        FakeMongoRepository([], []),
        FakeSqlRepository(),
    )

    with pytest.raises(HTTPException) as error:
        service.obtener(
            fecha_inicio=datetime(2026, 9, 30).date(),
            fecha_fin=datetime(2026, 10, 1).date(),
        )

    assert error.value.status_code == 400

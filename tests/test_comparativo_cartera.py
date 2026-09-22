from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.modules.analytic.cartera_de_credito.comparativo_cartera.dependencies import (
    get_comparativo_cartera_service,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.domain import (
    TotalesCartera,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.repositories.mongo_comparativo_cartera_repository import (
    MongoComparativoCarteraRepository,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.schemas import (
    CorteComparativoCartera,
    InputComparativoCartera,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.service import (
    ComparativoCarteraService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload


client = TestClient(app)


def fake_auth_context(fecha_sistema: date = date(2026, 9, 17)) -> AuthContext:
    return AuthContext.from_token_payload(
        "token",
        UsuarioTokenPayload(
            sub="jdoe",
            usuario="John Doe",
            id_agencia=1,
            nombre_agencia="Matriz",
            fecha_sistema=fecha_sistema,
        ),
    )


def totales(fecha_corte: date) -> TotalesCartera:
    return TotalesCartera(
        fecha_corte=fecha_corte,
        operaciones=3,
        saldo_capital=1000,
        capital_vigente=850,
        capital_no_devenga=100,
        capital_vencido=50,
        provision_requerida=75,
    )


class FakeRepository:
    def __init__(self) -> None:
        self.consultas_historicas: list[set[date]] = []
        self.actual_solicitada: date | None = None
        self.agencias: list[str] = []
        self.filtrar_diferidos: bool | None = None

    def obtener_historico(
        self,
        fechas: set[date],
        agencias: list[str],
        filtrar_diferidos: bool | None,
    ) -> dict[date, TotalesCartera]:
        self.consultas_historicas.append(set(fechas))
        self.agencias = agencias
        self.filtrar_diferidos = filtrar_diferidos
        return {fecha: totales(fecha) for fecha in fechas}

    def obtener_actual(
        self,
        fecha_corte: date,
        agencias: list[str],
        filtrar_diferidos: bool | None,
    ) -> TotalesCartera:
        self.actual_solicitada = fecha_corte
        self.agencias = agencias
        self.filtrar_diferidos = filtrar_diferidos
        return totales(fecha_corte)


class FakeCache:
    def __init__(self, datos: dict[date, TotalesCartera] | None = None) -> None:
        self.datos = datos or {}
        self.guardados: dict[date, TotalesCartera] = {}

    def obtener(
        self,
        fechas: set[date],
        agencias: list[str],
        filtrar_diferidos: bool | None,
    ) -> dict[date, TotalesCartera]:
        _ = agencias, filtrar_diferidos
        return {fecha: self.datos[fecha] for fecha in fechas if fecha in self.datos}

    def guardar(
        self,
        valores,
        agencias: list[str],
        filtrar_diferidos: bool | None,
    ) -> None:
        _ = agencias, filtrar_diferidos
        self.guardados.update({item.fecha_corte: item for item in valores})


class FakeMongoCollection:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.pipeline: list[dict] = []
        self.options: dict = {}

    def aggregate(self, pipeline: list[dict], **options) -> list[dict]:
        self.pipeline = pipeline
        self.options = options
        return self.rows


class FakeMongoDatabase:
    def __init__(self) -> None:
        row = {
            "_id": "20260916",
            "operaciones": 3,
            "saldo_capital": 1000,
            "capital_vigente": 850,
            "capital_no_devenga": 100,
            "capital_vencido": 50,
            "provision_requerida": 75,
        }
        self.collections = {
            "SituacionCrediticia": FakeMongoCollection([row]),
            "SituacionCrediticiaActual": FakeMongoCollection([]),
        }

    def __getitem__(self, name: str) -> FakeMongoCollection:
        return self.collections[name]


def test_input_requiere_fechas_del_mismo_mes() -> None:
    with pytest.raises(ValidationError):
        InputComparativoCartera(
            fecha_desde=date(2026, 8, 31),
            fecha_hasta=date(2026, 9, 1),
        )


def test_repositorio_agrupa_todos_los_cortes_en_una_consulta() -> None:
    database = FakeMongoDatabase()
    repository = MongoComparativoCarteraRepository(database)  # type: ignore[arg-type]

    resultado = repository.obtener_historico(
        {date(2026, 9, 15), date(2026, 9, 16)},
        ["MATRIZ"],
        True,
    )

    collection = database.collections["SituacionCrediticia"]
    match = collection.pipeline[0]["$match"]
    assert match["fecha_corte"] == {"$in": ["20260915", "20260916"]}
    assert match["EstadoPrestamo"] == {"$ne": "CANCELADO"}
    assert match["Agencia"] == {"$in": ["MATRIZ"]}
    assert "SI" in match["ESDIFERIDO"]["$in"]
    assert collection.options == {
        "hint": "fecha_corte_1_estado_prestamo_1",
        "allowDiskUse": True,
    }
    assert resultado[date(2026, 9, 16)].operaciones == 3


def test_pipeline_prioriza_provision_calculada() -> None:
    pipeline = MongoComparativoCarteraRepository._pipeline({}, "$fecha_corte")
    provision = pipeline[1]["$project"]["provision_requerida"]

    assert provision["$cond"][0]["$gt"][0]["$convert"]["input"] == (
        "$ProvisionRequeridaCalculada"
    )
    assert provision["$cond"][2]["$convert"]["input"] == "$ProvisionRequerida"


def test_repositorio_actual_usa_snapshot_completo_y_provision_requerida() -> None:
    database = FakeMongoDatabase()
    repository = MongoComparativoCarteraRepository(database)  # type: ignore[arg-type]

    repository.obtener_actual(
        date(2026, 9, 17),
        ["MATRIZ"],
        False,
    )

    collection = database.collections["SituacionCrediticiaActual"]
    match = collection.pipeline[0]["$match"]
    provision = collection.pipeline[1]["$project"]["provision_requerida"]
    assert "fecha_corte" not in match
    assert match["EstadoPrestamo"] == {"$ne": "CANCELADO"}
    assert match["Agencia"] == {"$in": ["MATRIZ"]}
    assert match["EsDiferido"] is False
    assert provision["$convert"]["input"] == "$ProvisionRequerida"


def test_servicio_resuelve_comparaciones_en_una_consulta_historica() -> None:
    repository = FakeRepository()
    service = ComparativoCarteraService(repository)  # type: ignore[arg-type]

    response = service.obtener_comparativo(
        InputComparativoCartera(
            fecha_desde=date(2026, 9, 15),
            fecha_hasta=date(2026, 9, 16),
            agencias=[" matriz ", "MATRIZ"],
            filtrar_diferidos=False,
        ),
        fake_auth_context(),
    )

    assert repository.actual_solicitada is None
    assert repository.agencias == ["MATRIZ"]
    assert repository.filtrar_diferidos is False
    assert len(repository.consultas_historicas) == 1
    assert set().union(*repository.consultas_historicas) == {
        date(2026, 9, 15),
        date(2026, 9, 16),
        date(2026, 8, 31),
        date(2025, 12, 31),
    }
    assert len(response.puntos) == 2
    assert response.puntos[0].actual is not None
    assert response.puntos[0].actual.cartera_improductiva == 150
    assert response.puntos[0].actual.morosidad_porcentaje == 15
    assert response.resumen_morosidad.actual.dias_con_datos == 2
    assert response.resumen_morosidad.actual.morosidad_promedio_ponderada_porcentaje == 15
    assert response.resumen_morosidad.mes_anterior.fecha_desde == date(2026, 8, 31)
    assert response.resumen_morosidad.mes_anterior.dias_con_datos == 1
    assert response.resumen_morosidad.anio_anterior.fecha_desde == date(2025, 12, 31)
    assert response.resumen_morosidad.anio_anterior.dias_con_datos == 1
    assert all(
        punto.mes_anterior is not None
        and punto.mes_anterior.fecha_corte == date(2026, 8, 31)
        and punto.anio_anterior is not None
        and punto.anio_anterior.fecha_corte == date(2025, 12, 31)
        for punto in response.puntos
    )


def test_servicio_usa_coleccion_actual_solo_para_hoy() -> None:
    repository = FakeRepository()
    service = ComparativoCarteraService(repository)  # type: ignore[arg-type]

    response = service.obtener_comparativo(
        InputComparativoCartera(
            fecha_desde=date(2026, 9, 16),
            fecha_hasta=date(2026, 9, 17),
        ),
        fake_auth_context(),
    )

    assert repository.actual_solicitada == date(2026, 9, 17)
    assert date(2026, 9, 17) not in set().union(*repository.consultas_historicas)
    assert response.puntos[-1].actual is not None
    assert response.puntos[-1].actual.fecha_corte == date(2026, 9, 17)


def test_servicio_usa_el_ultimo_dia_del_mes_anterior() -> None:
    repository = FakeRepository()
    service = ComparativoCarteraService(repository)  # type: ignore[arg-type]

    response = service.obtener_comparativo(
        InputComparativoCartera(
            fecha_desde=date(2026, 3, 30),
            fecha_hasta=date(2026, 3, 31),
        ),
        fake_auth_context(),
    )

    assert response.puntos[0].mes_anterior is not None
    assert response.puntos[0].mes_anterior.fecha_corte == date(2026, 2, 28)
    assert response.puntos[1].mes_anterior is not None
    assert response.puntos[1].mes_anterior.fecha_corte == date(2026, 2, 28)


def test_servicio_no_consulta_mongo_para_cortes_cacheados() -> None:
    repository = FakeRepository()
    fechas = {date(2026, 9, 16), date(2026, 8, 31), date(2025, 12, 31)}
    cache = FakeCache({fecha: totales(fecha) for fecha in fechas})
    service = ComparativoCarteraService(repository, cache=cache)  # type: ignore[arg-type]

    response = service.obtener_comparativo(
        InputComparativoCartera(
            fecha_desde=date(2026, 9, 16),
            fecha_hasta=date(2026, 9, 16),
        ),
        fake_auth_context(),
    )

    assert repository.consultas_historicas == []
    assert response.puntos[0].actual is not None
    assert response.puntos[0].mes_anterior is not None
    assert response.puntos[0].anio_anterior is not None


def test_resumen_morosidad_pondera_por_saldo_y_calcula_variacion() -> None:
    corte_inicial = CorteComparativoCartera(
        fecha_corte=date(2026, 9, 1),
        operaciones=1,
        saldo_capital=100,
        capital_vigente=90,
        capital_no_devenga=5,
        capital_vencido=5,
        cartera_improductiva=10,
        provision_requerida=1,
        morosidad=0.1,
        morosidad_porcentaje=10,
    )
    corte_final = CorteComparativoCartera(
        fecha_corte=date(2026, 9, 2),
        operaciones=1,
        saldo_capital=300,
        capital_vigente=240,
        capital_no_devenga=30,
        capital_vencido=30,
        cartera_improductiva=60,
        provision_requerida=2,
        morosidad=0.2,
        morosidad_porcentaje=20,
    )

    resumen = ComparativoCarteraService._resumir_morosidad(
        [corte_inicial, corte_final]
    )

    assert resumen.morosidad_promedio_ponderada_porcentaje == 17.5
    assert resumen.morosidad_minima_porcentaje == 10
    assert resumen.morosidad_maxima_porcentaje == 20
    assert resumen.variacion_puntos_porcentuales == 10


def test_servicio_rechaza_fecha_futura() -> None:
    service = ComparativoCarteraService(FakeRepository())  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as error:
        service.obtener_comparativo(
            InputComparativoCartera(
                fecha_desde=date(2026, 9, 17),
                fecha_hasta=date(2026, 9, 18),
            ),
            fake_auth_context(),
        )

    assert error.value.status_code == 400


def test_endpoint_devuelve_comparativo_y_requiere_bearer() -> None:
    unauthorized = client.post(
        "/analytic/cartera-de-credito/comparativo",
        json={"fecha_desde": "2026-09-16", "fecha_hasta": "2026-09-16"},
    )
    assert unauthorized.status_code == 401

    service = ComparativoCarteraService(FakeRepository())  # type: ignore[arg-type]
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_comparativo_cartera_service] = lambda: service
    try:
        response = client.post(
            "/analytic/cartera-de-credito/comparativo",
            json={"fecha_desde": "2026-09-16", "fecha_hasta": "2026-09-16"},
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_comparativo_cartera_service, None)

    assert response.status_code == 200
    body = response.json()
    assert body["consolidado"] is True
    assert body["resumen_morosidad"]["actual"]["dias_con_datos"] == 1
    assert body["resumen_morosidad"]["actual"][
        "morosidad_promedio_ponderada_porcentaje"
    ] == 15
    assert body["puntos"][0]["actual"]["saldo_capital"] == 1000
    assert body["puntos"][0]["mes_anterior"]["fecha_corte"] == "2026-08-31"
    assert body["puntos"][0]["anio_anterior"]["fecha_corte"] == "2025-12-31"


def test_endpoint_de_negocios_devuelve_resumen_actual_de_cartera() -> None:
    service = ComparativoCarteraService(FakeRepository())  # type: ignore[arg-type]
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_comparativo_cartera_service] = lambda: service
    try:
        response = client.post(
            "/negocios/cartera-de-credito/resumen-actual",
            json={"fecha_desde": "2026-09-16", "fecha_hasta": "2026-09-16"},
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_comparativo_cartera_service, None)

    assert response.status_code == 200
    assert response.json()["puntos"][0]["actual"]["saldo_capital"] == 1000

from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.cartera_de_credito.morosidad_historica.dependencies import (
    get_morosidad_historica_service,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.domain import (
    DimensionesMorosidad,
    MorosidadAgrupada,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.repositories.mongo_morosidad_historica_repository import (
    MongoMorosidadHistoricaRepository,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.schemas import (
    InputMorosidadHistorica,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.service import (
    MorosidadHistoricaService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload


client = TestClient(app)


def fake_auth_context(fecha_sistema: date = date(2026, 7, 22)) -> AuthContext:
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


def agrupacion(
    *,
    periodo: str = "2026-01",
    operaciones: int = 2,
    saldo_capital: float = 1000.0,
    capital_no_devenga: float = 100.0,
    capital_vencido: float = 50.0,
) -> MorosidadAgrupada:
    anio, mes = map(int, periodo.split("-"))
    return MorosidadAgrupada(
        dimensiones=DimensionesMorosidad(
            periodo=periodo,
            anio=anio,
            mes=mes,
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
        ),
        operaciones=operaciones,
        saldo_capital=saldo_capital,
        capital_vigente=saldo_capital - capital_no_devenga - capital_vencido,
        capital_no_devenga=capital_no_devenga,
        capital_vencido=capital_vencido,
    )


class FakeRepository:
    def __init__(self, datos: list[MorosidadAgrupada] | None = None) -> None:
        self.datos = datos or []
        self.cortes: dict[str, tuple[int, int]] = {}

    def obtener_morosidad_agrupada(
        self, cortes: dict[str, tuple[int, int]]
    ) -> list[MorosidadAgrupada]:
        self.cortes = cortes
        return list(self.datos)


class FakeMongoCollection:
    def __init__(self) -> None:
        self.pipeline: list[dict] = []
        self.options: dict = {}

    def aggregate(self, pipeline: list[dict], **options) -> list[dict]:
        self.pipeline = pipeline
        self.options = options
        return [
            {
                "_id": {
                    "fecha_corte": "20260131",
                    "agencia": "MATRIZ",
                    "condicion": "NUEVO",
                    "tipo_prestamo": "ORDINARIO",
                    "producto": "MICROCREDITO",
                    "segmento": "MINORISTA",
                    "asesor": "JUAN PEREZ",
                    "provincia": "AZUAY",
                    "canton": "CUENCA",
                    "parroquia": "EL VECINO",
                    "educacion": "SUPERIOR",
                    "edad": "HASTA 30",
                    "garantia": "PERSONAL",
                    "monto": "Hasta 3.000",
                    "tasa": "Hasta 16",
                    "tasa_valor": 16,
                    "tasa_real": "Hasta 17",
                    "tasa_real_valor": 17,
                    "plazo": "Hasta 2 AÑOS",
                    "plazo_valor": 730,
                },
                "operaciones": 2,
                "saldo_capital": 1000,
                "capital_no_devenga": 100,
                "capital_vencido": 50,
            }
        ]


class FakeMongoDatabase:
    def __init__(self) -> None:
        self.collection = FakeMongoCollection()

    def __getitem__(self, name: str) -> FakeMongoCollection:
        assert name == "SituacionCrediticia"
        return self.collection


def test_repositorio_consulta_solo_cortes_de_fin_de_mes() -> None:
    database = FakeMongoDatabase()
    repository = MongoMorosidadHistoricaRepository(database)  # type: ignore[arg-type]

    resultado = repository.obtener_morosidad_agrupada(
        {"20260131": (2026, 1), "20260228": (2026, 2)}
    )

    match = database.collection.pipeline[0]["$match"]
    assert match["fecha_corte"] == {"$in": ["20260131", "20260228"]}
    assert match["EstadoPrestamo"] == {"$ne": "CANCELADO"}
    project = database.collection.pipeline[1]["$project"]
    assert project["saldo_capital"]["$convert"]["input"] == "$SaldoCapital"
    assert project["capital_no_devenga"]["$convert"]["input"] == "$CapitalNoDevenga"
    assert project["capital_vencido"]["$convert"]["input"] == "$CapitalVencido"
    assert database.collection.options == {"hint": "fecha_corte_1", "allowDiskUse": True}
    assert resultado[0].capital_vigente == 850
    assert resultado[0].morosidad == 0.15


def test_servicio_calcula_morosidad_sobre_saldos_agrupados() -> None:
    repository = FakeRepository(
        [
            agrupacion(periodo="2026-01"),
            agrupacion(
                periodo="2026-02",
                operaciones=1,
                saldo_capital=500,
                capital_no_devenga=50,
                capital_vencido=50,
            ),
        ]
    )
    service = MorosidadHistoricaService(repository)  # type: ignore[arg-type]

    response = service.obtener_morosidad_historica(
        InputMorosidadHistorica(periodo_desde="2026-01", periodo_hasta="2026-02"),
        fake_auth_context(),
    )

    assert repository.cortes == {"20260131": (2026, 1), "20260228": (2026, 2)}
    assert response.operaciones == 3
    assert response.saldo_capital == 1500
    assert response.cartera_improductiva == 250
    assert response.morosidad == 0.166667
    assert response.morosidad_porcentaje == 16.6667
    assert response.resumen_mensual[0].morosidad == 0.15
    assert response.resumen_mensual[1].morosidad == 0.2
    assert response.periodos_sin_datos == []


def test_servicio_incluye_periodos_sin_datos() -> None:
    service = MorosidadHistoricaService(FakeRepository())  # type: ignore[arg-type]
    response = service.obtener_morosidad_historica(
        InputMorosidadHistorica(periodo_desde="2026-01", periodo_hasta="2026-02"),
        fake_auth_context(),
    )

    assert [item.fecha_corte for item in response.resumen_mensual] == [
        "20260131",
        "20260228",
    ]
    assert response.periodos_sin_datos == ["2026-01", "2026-02"]
    assert response.morosidad == 0


def test_servicio_rechaza_mes_que_no_ha_finalizado() -> None:
    service = MorosidadHistoricaService(FakeRepository())  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as error:
        service.obtener_morosidad_historica(
            InputMorosidadHistorica(periodo_desde="2026-07", periodo_hasta="2026-07"),
            fake_auth_context(date(2026, 7, 22)),
        )

    assert error.value.status_code == 400
    assert error.value.detail == "periodo_hasta debe corresponder a un mes finalizado."


def test_endpoint_requiere_token() -> None:
    response = client.post(
        "/analytic/cartera-de-credito/morosidad-historica",
        json={"periodo_desde": "2026-01", "periodo_hasta": "2026-02"},
    )
    assert response.status_code == 401


def test_endpoint_devuelve_agrupaciones_y_resumen_mensual() -> None:
    service = MorosidadHistoricaService(  # type: ignore[arg-type]
        FakeRepository([agrupacion()])
    )
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_morosidad_historica_service] = lambda: service
    try:
        response = client.post(
            "/analytic/cartera-de-credito/morosidad-historica",
            json={"periodo_desde": "2026-01", "periodo_hasta": "2026-01"},
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_morosidad_historica_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["resumen_mensual"][0]["fecha_corte"] == "20260131"
    assert payload["agrupaciones"][0]["agencia"] == "MATRIZ"
    assert payload["agrupaciones"][0]["cartera_improductiva"] == 150
    assert payload["agrupaciones"][0]["morosidad_porcentaje"] == 15


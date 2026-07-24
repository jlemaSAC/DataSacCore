from datetime import date
from collections.abc import Iterable
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.cartera_de_credito.morosidad_historica.dependencies import (
    get_morosidad_historica_cache_admin_service,
    get_morosidad_historica_service,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.domain import (
    CorteActualMorosidad,
    DimensionesMorosidad,
    MorosidadAgrupada,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.repositories.mongo_morosidad_historica_repository import (
    MongoMorosidadHistoricaRepository,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.repositories.redis_morosidad_historica_cache import (
    RedisMorosidadHistoricaCache,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.schemas import (
    InputMorosidadHistorica,
    MorosidadHistoricaAgrupacion,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.service import (
    MorosidadHistoricaCacheAdminService,
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
    saldo_capital: float = 1000.0,
    cartera_improductiva: float = 150.0,
    provision_requerida: float = 75.0,
    operaciones: int = 3,
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
            tasa_real="Hasta 17",
            plazo="Hasta 2 AÑOS",
            cuota="Hasta 500",
        ),
        operaciones=operaciones,
        saldo_capital=saldo_capital,
        cartera_improductiva=cartera_improductiva,
        provision_requerida=provision_requerida,
    )


class FakeRepository:
    def __init__(self, datos: list[MorosidadAgrupada] | None = None) -> None:
        self.datos = datos or []
        self.cortes: dict[str, tuple[int, int]] = {}
        self.corte_actual: CorteActualMorosidad | None = None
        self.calls = 0

    def obtener_morosidad_agrupada(
        self,
        cortes: dict[str, tuple[int, int]],
        corte_actual: CorteActualMorosidad | None = None,
    ) -> list[MorosidadAgrupada]:
        self.calls += 1
        self.cortes = cortes
        self.corte_actual = corte_actual
        return list(self.datos)


class FakeCache:
    def __init__(
        self, datos: dict[str, list[MorosidadHistoricaAgrupacion]] | None = None
    ) -> None:
        self.datos = datos or {}
        self.periodos_solicitados: list[str] = []
        self.periodos_guardados: dict[str, list[MorosidadHistoricaAgrupacion]] = {}

    def obtener_meses(
        self, periodos: Iterable[str]
    ) -> dict[str, list[MorosidadHistoricaAgrupacion]]:
        self.periodos_solicitados = list(periodos)
        return {
            periodo: self.datos[periodo]
            for periodo in self.periodos_solicitados
            if periodo in self.datos
        }

    def guardar_mes(
        self, periodo: str, agrupaciones: list[MorosidadHistoricaAgrupacion]
    ) -> None:
        self.periodos_guardados[periodo] = agrupaciones


class FakeRedisClient:
    def __init__(self, valores: dict[str, str]) -> None:
        self.valores = valores

    def scan_iter(self, *, match: str, count: int) -> Iterable[str]:
        _ = count
        prefijo = match.removesuffix("*")
        return iter([clave for clave in self.valores if clave.startswith(prefijo)])

    def unlink(self, *claves: str) -> int:
        eliminadas = 0
        for clave in claves:
            if clave in self.valores:
                del self.valores[clave]
                eliminadas += 1
        return eliminadas


class FakeCacheAdmin:
    def __init__(self, claves_eliminadas: int = 0) -> None:
        self.claves_eliminadas = claves_eliminadas
        self.llamadas = 0

    def limpiar_cache(self) -> int:
        self.llamadas += 1
        return self.claves_eliminadas


class FakeSqlAuthRepository:
    def __init__(self, roles: list[str]) -> None:
        self.roles = roles

    def get_roles_usuario(self, codigo_usuario: str) -> list[SimpleNamespace]:
        _ = codigo_usuario
        return [SimpleNamespace(codigo=rol) for rol in self.roles]


class FakeMongoCollection:
    def __init__(self, fecha_corte: str) -> None:
        self.fecha_corte = fecha_corte
        self.pipeline: list[dict] = []
        self.options: dict = {}

    def aggregate(self, pipeline: list[dict], **options) -> list[dict]:
        self.pipeline = pipeline
        self.options = options
        return [
            {
                "_id": {
                    "fecha_corte": self.fecha_corte,
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
                    "tasa_real": "Hasta 17",
                    "plazo": "Hasta 2 AÑOS",
                    "cuota": "Hasta 500",
                },
                "operaciones": 3,
                "saldo_capital": 1000,
                "cartera_improductiva": 150,
                "provision_requerida": 75,
            }
        ]


class FakeMongoDatabase:
    def __init__(self) -> None:
        self.collections = {
            "SituacionCrediticia": FakeMongoCollection("20260131"),
            "SituacionCrediticiaActual": FakeMongoCollection("20260722"),
        }

    def __getitem__(self, name: str) -> FakeMongoCollection:
        return self.collections[name]


def test_repositorio_consulta_solo_cortes_de_fin_de_mes() -> None:
    database = FakeMongoDatabase()
    repository = MongoMorosidadHistoricaRepository(database)  # type: ignore[arg-type]

    resultado = repository.obtener_morosidad_agrupada(
        {"20260131": (2026, 1), "20260228": (2026, 2)}
    )

    collection = database.collections["SituacionCrediticia"]
    match = collection.pipeline[0]["$match"]
    assert match["fecha_corte"] == {"$in": ["20260131", "20260228"]}
    assert match["EstadoPrestamo"] == {"$ne": "CANCELADO"}
    project = collection.pipeline[1]["$project"]
    assert project["saldo_capital"]["$convert"]["input"] == "$SaldoCapital"
    sumandos = project["cartera_improductiva"]["$add"]
    assert sumandos[0]["$convert"]["input"] == "$CapitalNoDevenga"
    assert sumandos[1]["$convert"]["input"] == "$CapitalVencido"
    assert project["provision_requerida"]["$convert"]["input"] == "$ProvisionRequerida"
    assert collection.pipeline[2]["$group"]["operaciones"] == {"$sum": 1}
    dimensiones_grupo = collection.pipeline[2]["$group"]["_id"]
    assert "tasa_valor" not in dimensiones_grupo
    assert "tasa_real_valor" not in dimensiones_grupo
    assert "plazo_valor" not in dimensiones_grupo
    assert collection.options == {
        "hint": "fecha_corte_1_estado_prestamo_1",
        "allowDiskUse": True,
    }
    assert resultado[0].saldo_capital == 1000
    assert resultado[0].operaciones == 3
    assert resultado[0].cartera_improductiva == 150
    assert resultado[0].provision_requerida == 75
    assert resultado[0].dimensiones.cuota == "Hasta 500"


def test_pipeline_calcula_rango_cuota_con_datos_fuente() -> None:
    database = FakeMongoDatabase()
    repository = MongoMorosidadHistoricaRepository(database)  # type: ignore[arg-type]
    repository.obtener_morosidad_agrupada({"20260131": (2026, 1)})

    cuota = database.collections["SituacionCrediticia"].pipeline[1]["$project"]["cuota"]
    assert [branch["then"] for branch in cuota["$switch"]["branches"]] == [
        "Hasta 100",
        "Hasta 300",
        "Hasta 500",
        "Hasta 700",
        "Hasta 900",
        "Hasta 1.100",
        "Hasta 1.300",
        "Hasta 1.500",
        "Hasta 1.700",
        "Hasta 1.900",
        "Mas de 1.900",
    ]
    calculo = cuota["$switch"]["branches"][0]["case"]["$and"][0]["$ne"][0]
    datos_validos = calculo["$cond"][0]["$and"]
    assert datos_validos[0]["$ne"][0]["$convert"]["input"] == "$DeudaInicial"
    assert datos_validos[2]["$ne"][0]["$convert"]["input"] == "$TasaNominal"
    assert datos_validos[4]["$ne"][0]["$convert"]["input"] == "$Plazo"
    assert cuota["$switch"]["default"] == "SIN DATOS"


def test_repositorio_consulta_mes_actual_en_situacion_crediticia_actual() -> None:
    database = FakeMongoDatabase()
    repository = MongoMorosidadHistoricaRepository(database)  # type: ignore[arg-type]

    resultado = repository.obtener_morosidad_agrupada(
        {},
        CorteActualMorosidad(fecha_corte="20260722", anio=2026, mes=7),
    )

    collection = database.collections["SituacionCrediticiaActual"]
    assert collection.pipeline[0]["$match"] == {
        "EstadoPrestamo": {"$ne": "CANCELADO"}
    }
    assert collection.pipeline[1]["$project"]["fecha_corte"] == {
        "$literal": "20260722"
    }
    plazo = collection.pipeline[1]["$project"]["plazo"]
    assert plazo["$switch"]["branches"][0]["then"] == "Hasta 1 AÑO"
    condicion_plazo = plazo["$switch"]["branches"][0]["case"]["$and"]
    assert condicion_plazo[1]["$lte"][0]["$cond"][0]["$gte"][0]["$convert"][
        "input"
    ] == "$Plazo"
    assert condicion_plazo[1]["$lte"][1] == 12
    assert plazo["$switch"]["default"] == "SIN DATOS"
    assert collection.options == {"allowDiskUse": True}
    assert resultado[0].dimensiones.periodo == "2026-07"


def test_servicio_devuelve_metricas_por_agrupacion() -> None:
    repository = FakeRepository(
        [
            agrupacion(periodo="2026-01"),
            agrupacion(
                periodo="2026-02",
                saldo_capital=500,
                cartera_improductiva=100,
            ),
        ]
    )
    service = MorosidadHistoricaService(repository)  # type: ignore[arg-type]

    response = service.obtener_morosidad_historica(
        InputMorosidadHistorica(periodo_desde="2026-01", periodo_hasta="2026-02"),
        fake_auth_context(),
    )

    assert repository.cortes == {"20260131": (2026, 1), "20260228": (2026, 2)}
    assert repository.corte_actual is None
    payload = response.model_dump()
    assert set(payload) == {"agrupaciones"}
    assert len(payload["agrupaciones"]) == 2
    metricas = {"operaciones", "saldo_capital", "cartera_improductiva", "provision_requerida"}
    for item in payload["agrupaciones"]:
        assert metricas <= item.keys()
        assert {
            "capital_vigente",
            "capital_no_devenga",
            "capital_vencido",
            "morosidad",
            "morosidad_porcentaje",
        }.isdisjoint(item)


def test_servicio_sin_datos_devuelve_agrupaciones_vacias() -> None:
    service = MorosidadHistoricaService(FakeRepository())  # type: ignore[arg-type]
    response = service.obtener_morosidad_historica(
        InputMorosidadHistorica(periodo_desde="2026-01", periodo_hasta="2026-02"),
        fake_auth_context(),
    )

    assert response.agrupaciones == []


def test_servicio_reutiliza_meses_cacheados_y_consulta_solo_los_faltantes() -> None:
    enero = agrupacion(periodo="2026-01", saldo_capital=100)
    febrero = agrupacion(periodo="2026-02", saldo_capital=200)
    cache = FakeCache(
        {"2026-01": MorosidadHistoricaService._construir_agrupaciones([enero])}
    )
    repository = FakeRepository([febrero])
    service = MorosidadHistoricaService(repository, cache=cache)  # type: ignore[arg-type]

    response = service.obtener_morosidad_historica(
        InputMorosidadHistorica(periodo_desde="2026-01", periodo_hasta="2026-02"),
        fake_auth_context(),
    )

    assert cache.periodos_solicitados == ["2026-01", "2026-02"]
    assert repository.calls == 1
    assert repository.cortes == {"20260228": (2026, 2)}
    assert [item.periodo for item in response.agrupaciones] == ["2026-01", "2026-02"]
    assert [item.saldo_capital for item in response.agrupaciones] == [100, 200]
    assert list(cache.periodos_guardados) == ["2026-02"]


def test_servicio_no_consulta_mongo_cuando_todos_los_meses_cerrados_estan_cacheados() -> None:
    enero = agrupacion(periodo="2026-01", saldo_capital=100)
    febrero = agrupacion(periodo="2026-02", saldo_capital=200)
    cache = FakeCache(
        {
            "2026-01": MorosidadHistoricaService._construir_agrupaciones([enero]),
            "2026-02": MorosidadHistoricaService._construir_agrupaciones([febrero]),
        }
    )
    repository = FakeRepository()
    service = MorosidadHistoricaService(repository, cache=cache)  # type: ignore[arg-type]

    response = service.obtener_morosidad_historica(
        InputMorosidadHistorica(periodo_desde="2026-01", periodo_hasta="2026-02"),
        fake_auth_context(),
    )

    assert repository.cortes == {}
    assert repository.corte_actual is None
    assert repository.calls == 0
    assert [item.periodo for item in response.agrupaciones] == ["2026-01", "2026-02"]
    assert cache.periodos_guardados == {}


def test_servicio_no_cachea_el_mes_actual() -> None:
    cache = FakeCache({"2026-07": MorosidadHistoricaService._construir_agrupaciones([])})
    repository = FakeRepository([agrupacion(periodo="2026-07")])
    service = MorosidadHistoricaService(repository, cache=cache)  # type: ignore[arg-type]

    response = service.obtener_morosidad_historica(
        InputMorosidadHistorica(periodo_desde="2026-07", periodo_hasta="2026-07"),
        fake_auth_context(date(2026, 7, 22)),
    )

    assert cache.periodos_solicitados == []
    assert repository.calls == 1
    assert repository.cortes == {}
    assert repository.corte_actual == CorteActualMorosidad("20260722", 2026, 7)
    assert [item.periodo for item in response.agrupaciones] == ["2026-07"]


def test_cache_limpia_solo_las_claves_de_morosidad_historica() -> None:
    valores = {
        "cartera:morosidad-historica:v1:2026-01": "enero",
        "cartera:morosidad-historica:v1:2026-02": "febrero",
        "cartera:colocacion-historica:v1:2026-01": "no eliminar",
        "otra-aplicacion:clave": "no eliminar",
    }
    cache = RedisMorosidadHistoricaCache(FakeRedisClient(valores))  # type: ignore[arg-type]

    eliminadas = cache.limpiar_cache()

    assert eliminadas == 2
    assert valores == {
        "cartera:colocacion-historica:v1:2026-01": "no eliminar",
        "otra-aplicacion:clave": "no eliminar",
    }


def test_servicio_admin_limpia_cache_solo_para_rol_administrador() -> None:
    cache = FakeCacheAdmin(claves_eliminadas=4)
    service = MorosidadHistoricaCacheAdminService(  # type: ignore[arg-type]
        cache=cache,
        sql_repository=FakeSqlAuthRepository(["001"]),
    )

    respuesta = service.limpiar_cache(fake_auth_context())

    assert respuesta.claves_eliminadas == 4
    assert cache.llamadas == 1


def test_servicio_admin_rechaza_limpieza_sin_rol_administrador() -> None:
    service = MorosidadHistoricaCacheAdminService(  # type: ignore[arg-type]
        cache=FakeCacheAdmin(),
        sql_repository=FakeSqlAuthRepository(["002"]),
    )

    with pytest.raises(HTTPException) as error:
        service.limpiar_cache(fake_auth_context())

    assert error.value.status_code == 403


def test_endpoint_admin_limpia_cache_de_morosidad_historica() -> None:
    cache = FakeCacheAdmin(claves_eliminadas=3)
    service = MorosidadHistoricaCacheAdminService(  # type: ignore[arg-type]
        cache=cache,
        sql_repository=FakeSqlAuthRepository(["001"]),
    )
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_morosidad_historica_cache_admin_service] = lambda: service
    try:
        response = client.delete("/analytic/cartera-de-credito/morosidad-historica/cache")
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_morosidad_historica_cache_admin_service, None)

    assert response.status_code == 200
    assert response.json() == {"claves_eliminadas": 3}
    assert cache.llamadas == 1


def test_servicio_usa_coleccion_actual_para_mes_en_curso() -> None:
    repository = FakeRepository([agrupacion(periodo="2026-07")])
    service = MorosidadHistoricaService(repository)  # type: ignore[arg-type]

    response = service.obtener_morosidad_historica(
        InputMorosidadHistorica(periodo_desde="2026-07", periodo_hasta="2026-07"),
        fake_auth_context(date(2026, 7, 22)),
    )

    assert repository.cortes == {}
    assert repository.corte_actual == CorteActualMorosidad(
        fecha_corte="20260722",
        anio=2026,
        mes=7,
    )
    assert response.agrupaciones[0].periodo == "2026-07"


def test_servicio_rechaza_mes_futuro() -> None:
    service = MorosidadHistoricaService(FakeRepository())  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as error:
        service.obtener_morosidad_historica(
            InputMorosidadHistorica(periodo_desde="2026-08", periodo_hasta="2026-08"),
            fake_auth_context(date(2026, 7, 22)),
        )

    assert error.value.status_code == 400
    assert error.value.detail == "periodo_hasta no puede ser posterior al mes actual."


def test_endpoint_requiere_token() -> None:
    response = client.post(
        "/analytic/cartera-de-credito/morosidad-historica",
        json={"periodo_desde": "2026-01", "periodo_hasta": "2026-02"},
    )
    assert response.status_code == 401


def test_endpoint_devuelve_agrupaciones_con_metricas() -> None:
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
    assert set(payload) == {"agrupaciones"}
    assert payload["agrupaciones"][0]["agencia"] == "MATRIZ"
    assert payload["agrupaciones"][0]["saldo_capital"] == 1000
    assert payload["agrupaciones"][0]["operaciones"] == 3
    assert payload["agrupaciones"][0]["cartera_improductiva"] == 150
    assert payload["agrupaciones"][0]["provision_requerida"] == 75
    assert payload["agrupaciones"][0]["cuota"] == "Hasta 500"
    assert "morosidad" not in payload["agrupaciones"][0]
    assert "morosidad_porcentaje" not in payload["agrupaciones"][0]
    assert "tasa_valor" not in payload["agrupaciones"][0]
    assert "tasa_real_valor" not in payload["agrupaciones"][0]
    assert "plazo_valor" not in payload["agrupaciones"][0]

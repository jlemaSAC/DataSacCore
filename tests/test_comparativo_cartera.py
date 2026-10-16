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
    PrestamoResumenCartera,
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
        self.resumen_agencias_fecha: date | None = None
        self.resumen_agencias_actual: bool | None = None
        self.resumen_agencias_filtro: list[str] = []
        self.resumen_filtros: tuple | None = None

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

    def obtener_por_agencia(
        self,
        fecha_corte: date,
        agencias: list[str],
        filtrar_diferidos: bool | None,
        *,
        actual: bool,
    ) -> dict[str, TotalesCartera]:
        self.resumen_agencias_fecha = fecha_corte
        self.resumen_agencias_actual = actual
        self.resumen_agencias_filtro = agencias
        self.filtrar_diferidos = filtrar_diferidos
        resultados = {
            "MATRIZ": totales(fecha_corte),
            "AGENCIA B": TotalesCartera(
                fecha_corte=fecha_corte,
                operaciones=1,
                saldo_capital=200,
                capital_vigente=150,
                capital_no_devenga=30,
                capital_vencido=20,
                provision_requerida=10,
            ),
        }
        return {
            agencia: total
            for agencia, total in resultados.items()
            if not agencias or agencia in agencias
        }

    def obtener_prestamos_resumen(
        self, fecha_corte: date, agencias: list[str], filtrar_diferidos: bool | None,
        *, actual: bool,
    ) -> list[PrestamoResumenCartera]:
        self.resumen_filtros = (fecha_corte, agencias, filtrar_diferidos, actual)
        return [
            PrestamoResumenCartera(
                numero_prestamo=str(indice), cliente=cliente,
                dimensiones={"agencia": "MATRIZ", "producto": producto},
                saldo_capital=saldo, cartera_improductiva=saldo * 0.15,
                provision_requerida=saldo * 0.075,
            )
            for indice, (cliente, producto, saldo) in enumerate([
                ("1", "MICROCREDITO", 600),
                ("1", "MICROCREDITO", 200),
                ("2", "CONSUMO", 200),
            ])
        ]


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


def test_repositorio_por_agencia_aplica_filtro_de_agencias() -> None:
    database = FakeMongoDatabase()
    database.collections["SituacionCrediticia"].rows = [
        {
            "_id": "MATRIZ",
            "operaciones": 2,
            "saldo_capital": 1200,
            "capital_no_devenga": 100,
            "capital_vencido": 50,
            "provision_requerida": 30,
        }
    ]
    repository = MongoComparativoCarteraRepository(database)  # type: ignore[arg-type]

    resultado = repository.obtener_por_agencia(
        date(2026, 9, 16), ["MATRIZ"], False, actual=False
    )

    collection = database.collections["SituacionCrediticia"]
    match = collection.pipeline[0]["$match"]
    assert match["Agencia"] == {"$in": ["MATRIZ"]}
    assert match["fecha_corte"] == "20260916"
    assert match["ESDIFERIDO"]["$nin"]
    assert resultado["MATRIZ"].saldo_capital == 1200
    assert resultado["MATRIZ"].cartera_improductiva == 150


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
    assert [item.agencia for item in response.resumen_por_agencia] == ["MATRIZ"]
    assert response.resumen_por_agencia[0].saldo_capital == 1000
    assert response.resumen_por_agencia[0].morosidad_porcentaje == 15
    assert response.resumen_por_agencia[0].cartera_improductiva == 150
    assert response.resumen_por_agencia[0].provision_requerida == 75
    assert repository.resumen_agencias_filtro == ["MATRIZ"]
    assert repository.resumen_agencias_fecha == date(2026, 9, 16)
    assert repository.resumen_agencias_actual is False
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
    assert body["fecha_corte_resumen"] == "2026-09-16"
    assert len(body["resumen_por_dimension"]) == 8
    assert body["resumen_por_dimension"][0]["filas"] == [{
        "campo": "MATRIZ", "saldo_capital": 1000,
        "participacion_saldo_porcentaje": 100, "operaciones": 3, "clientes": 2,
        "cartera_improductiva": 150,
        "provision_requerida": 75, "morosidad_porcentaje": 15,
    }]


def test_endpoint_de_negocios_devuelve_resumen_actual_de_cartera() -> None:
    service = ComparativoCarteraService(FakeRepository())  # type: ignore[arg-type]
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_comparativo_cartera_service] = lambda: service
    try:
        response = client.post(
            "/negocios/cartera-de-credito/resumen-actual",
            json={
                "fecha_desde": "2026-09-16",
                "fecha_hasta": "2026-09-16",
                "agencias": ["MATRIZ"],
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_comparativo_cartera_service, None)

    assert response.status_code == 200
    assert response.json()["puntos"][0]["actual"]["saldo_capital"] == 1000
    resumen = response.json()["resumen_por_agencia"]
    assert [item["agencia"] for item in resumen] == ["MATRIZ"]
    assert resumen[0]["saldo_capital"] == 1000
    assert resumen[0]["morosidad_porcentaje"] == 15
    assert resumen[0]["cartera_improductiva"] == 150
    assert resumen[0]["provision_requerida"] == 75
    assert response.json()["resumen_por_dimension"][0]["filas"][0]["cartera_improductiva"] == 150


@pytest.mark.parametrize('actual,diferidos', [(True, True), (True, False), (False, True), (False, False), (False, None)])
def test_repositorio_tabla_aplica_filtros_y_fuente(actual: bool, diferidos: bool | None) -> None:
    database = FakeMongoDatabase()
    nombre = 'SituacionCrediticiaActual' if actual else 'SituacionCrediticia'
    database.collections[nombre].rows = [{
        'numero_prestamo': '001', 'cliente': '17',
        'dimensiones': {'agencia': 'MATRIZ'}, 'saldo_capital': 100,
        'cartera_improductiva': 10, 'provision_requerida': 2,
    }]
    repository = MongoComparativoCarteraRepository(database)  # type: ignore[arg-type]
    rows = repository.obtener_prestamos_resumen(date(2026, 9, 16), ['MATRIZ'], diferidos, actual=actual)
    collection = database.collections[nombre]
    match = collection.pipeline[0]['$match']
    assert match['Agencia'] == {'$in': ['MATRIZ']}
    assert match['EstadoPrestamo'] == {'$ne': 'CANCELADO'}
    assert ('fecha_corte' in match) is not actual
    if actual:
        assert match['EsDiferido'] is diferidos
        assert collection.pipeline[1]['$project']['provision_requerida']['$convert']['input'] == '$ProvisionRequerida'
    else:
        assert match['fecha_corte'] == '20260916'
        assert collection.options['hint'] == 'fecha_corte_1_estado_prestamo_1'
        if diferidos is not None:
            assert ('$in' if diferidos else '$nin') in match['ESDIFERIDO']
    assert rows[0].cliente == '17'
    assert rows[0].numero_prestamo == '001'


def test_tabla_cuenta_clientes_distintos_y_calcula_participacion_y_mora() -> None:
    repository = FakeRepository()
    service = ComparativoCarteraService(repository)  # type: ignore[arg-type]
    response = service.obtener_comparativo(InputComparativoCartera(
        fecha_desde=date(2026, 9, 16), fecha_hasta=date(2026, 9, 17),
        agencias=['MATRIZ'], filtrar_diferidos=True,
    ), fake_auth_context())
    assert repository.resumen_filtros == (date(2026, 9, 17), ['MATRIZ'], True, True)
    productos = next(item.filas for item in response.resumen_por_dimension if item.dimension == 'producto')
    assert [item.campo for item in productos] == ['MICROCREDITO', 'CONSUMO']
    assert [item.participacion_saldo_porcentaje for item in productos] == [80, 20]
    assert productos[0].operaciones == 2
    assert productos[0].clientes == 1
    assert productos[0].morosidad_porcentaje == 15
    assert [item.cartera_improductiva for item in productos] == [120, 30]
    for dimension in response.resumen_por_dimension:
        assert sum(item.cartera_improductiva for item in dimension.filas) == 150
    responsable = next(item.filas for item in response.resumen_por_dimension if item.dimension == 'usuario_responsable_control')
    assert responsable[0].campo == 'SIN DATOS'


def test_tabla_usa_ultimo_corte_disponible_sin_sumar_cortes_diarios() -> None:
    class RepositorySinUltimoCorte(FakeRepository):
        def obtener_actual(self, *args, **kwargs):
            return None
    repository = RepositorySinUltimoCorte()
    service = ComparativoCarteraService(repository)  # type: ignore[arg-type]
    response = service.obtener_comparativo(InputComparativoCartera(
        fecha_desde=date(2026, 9, 16), fecha_hasta=date(2026, 9, 17),
    ), fake_auth_context())
    assert response.fecha_corte_resumen == date(2026, 9, 16)
    assert repository.resumen_filtros == (date(2026, 9, 16), [], None, False)
    assert response.resumen_por_dimension[0].filas[0].saldo_capital == 1000
    assert response.resumen_por_dimension[0].filas[0].cartera_improductiva == 150


def test_tabla_vacia_no_consulta_detalle_ni_sql() -> None:
    class RepositorySinDatos(FakeRepository):
        def obtener_historico(self, *args, **kwargs):
            return {}
    repository = RepositorySinDatos()
    response = ComparativoCarteraService(repository).obtener_comparativo(  # type: ignore[arg-type]
        InputComparativoCartera(fecha_desde=date(2026, 9, 16), fecha_hasta=date(2026, 9, 16)),
        fake_auth_context(),
    )
    assert response.fecha_corte_resumen is None
    assert response.resumen_por_dimension == []
    assert repository.resumen_filtros is None


def test_tabla_saldo_cero_no_divide_para_cero() -> None:
    rows = ComparativoCarteraService._resumir_dimensiones([
        PrestamoResumenCartera('1', '2', {'agencia': ''}, 0, 0, 0),
    ], {})
    fila = rows[0].filas[0]
    assert fila.campo == 'SIN DATOS'
    assert fila.participacion_saldo_porcentaje == 0
    assert fila.morosidad_porcentaje == 0
    assert fila.cartera_improductiva == 0


def test_tabla_redondea_cartera_improductiva_despues_de_sumar_el_grupo() -> None:
    rows = ComparativoCarteraService._resumir_dimensiones([
        PrestamoResumenCartera('1', '1', {'agencia': 'MATRIZ'}, 100, 10.004, 0),
        PrestamoResumenCartera('2', '2', {'agencia': 'MATRIZ'}, 100, 20.004, 0),
    ], {})
    assert rows[0].filas[0].cartera_improductiva == 30.01


def test_tabla_completa_clientes_del_snapshot_desde_sql() -> None:
    class RepositorySinClientes(FakeRepository):
        def obtener_prestamos_resumen(self, *args, **kwargs):
            return [PrestamoResumenCartera(str(i), None, {'agencia': 'MATRIZ'}, 100, 10, 5) for i in range(2)]
    class ClientesRepository:
        def obtener_clientes(self, numeros):
            assert numeros == ['0', '1']
            return {'0': '17', '1': '17'}
    service = ComparativoCarteraService(RepositorySinClientes(), clientes_repository=ClientesRepository())  # type: ignore[arg-type]
    response = service.obtener_comparativo(InputComparativoCartera(
        fecha_desde=date(2026, 9, 17), fecha_hasta=date(2026, 9, 17),
    ), fake_auth_context())
    assert response.resumen_por_dimension[0].filas[0].clientes == 1
    assert response.resumen_por_dimension[0].filas[0].operaciones == 2


def test_sql_clientes_parametriza_y_divide_lotes_sin_duplicar_numeros() -> None:
    from app.modules.analytic.cartera_de_credito.comparativo_cartera.repositories.sql_clientes_cartera_repository import SqlClientesCarteraRepository
    class Result:
        def mappings(self):
            return [{'numero_prestamo': '001', 'numero_cliente': 17}]
    class Database:
        def __init__(self):
            self.calls = []
        def execute(self, statement, params):
            assert 'INNER JOIN COLOCACION.PRESTAMO_CLIENTE' in str(statement)
            assert 'PC.ESPRINCIPAL = 1 AND PC.ACTIVO = 1' in str(statement)
            self.calls.append(params['numeros'])
            return Result()
    database = Database()
    repository = SqlClientesCarteraRepository(database)  # type: ignore[arg-type]
    repository.batch_size = 2
    assert repository.obtener_clientes(['003', '001', '002', '001']) == {'001': '17'}
    assert database.calls == [['001', '002'], ['003']]
    database.calls.clear()
    assert repository.obtener_clientes([]) == {}
    assert database.calls == []

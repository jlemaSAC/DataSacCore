from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.dependencies import (
    get_resumen_diario_cartera_service,
)
from app.modules.negocios.router import router as negocios_router
from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.service import (
    ResumenDiarioCarteraService,
)
from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.repositories.mongo_resumen_diario_cartera_repository import (
    MongoResumenDiarioCarteraRepository,
)


class FakeMongoRepository:
    def obtener_snapshots_por_agencia(self, **kwargs) -> dict[str, list[dict]]:
        assert kwargs["agencia"] == "Ambato"
        assert kwargs["fecha_corte_ayer"] == "20261004"
        return {
            "hoy": [
                {
                    "NumeroPrestamo": "L-100",
                    "CodigoUsuario": "ana",
                    "NombreAsesor": "Ana",
                    "Agencia": "Ambato",
                    "SaldoCapital": 1000,
                    "ProvisionRequerida": 20,
                    "CapitalNoDevenga": 30,
                    "CapitalVencido": 70,
                    "DiasVencidos": 1,
                },
                {
                    "NumeroPrestamo": "L-200",
                    "CodigoUsuario": "ana",
                    "NombreAsesor": "Ana",
                    "Agencia": "Ambato",
                    "SaldoCapital": 1000,
                    "ProvisionRequerida": 80,
                    "CapitalNoDevenga": 20,
                    "CapitalVencido": 80,
                    "DiasVencidos": 2,
                },
            ],
            "ayer": [
                {
                    "NumeroPrestamo": "L-100",
                    "CodigoUsuario": "carlos",
                    "NombreAsesor": "Carlos",
                    "Agencia": "Ambato",
                    "SaldoCapital": 800,
                    "ProvisionRequerida": 15,
                    "CapitalNoDevenga": 20,
                    "CapitalVencido": 30,
                    "DiasVencidos": 0,
                },
                {
                    "NumeroPrestamo": "L-300",
                    "CodigoUsuario": "carlos",
                    "NombreAsesor": "Carlos",
                    "Agencia": "Ambato",
                    "SaldoCapital": 400,
                    "ProvisionRequerida": 5,
                    "CapitalNoDevenga": 10,
                    "CapitalVencido": 20,
                    "DiasVencidos": 2,
                },
            ],
        }


class FakeSqlAgencyRepository:
    def obtener_nombre_agencia(self, id_agencia: int) -> str | None:
        assert id_agencia == 4
        return "Ambato"


def test_resumen_diario_cartera_calcula_morosidad_por_agencia_y_asesor() -> None:
    auth_context = AuthContext(
        usuario=UsuarioTokenPayload(
            sub="ana",
            usuario="Ana",
            id_agencia=4,
            fecha_sistema=date(2026, 10, 5),
        ),
        token="token",
    )
    service = ResumenDiarioCarteraService(FakeSqlAgencyRepository(), FakeMongoRepository())

    respuesta = service.obtener(id_agencia=4, auth_context=auth_context)

    assert respuesta.fecha == date(2026, 10, 5)
    assert respuesta.resumen.hoy.saldo_capital == 2000
    assert respuesta.resumen.hoy.provision_requerida == 100
    assert respuesta.resumen.hoy.creditos_en_mora == 2
    assert respuesta.resumen.hoy.creditos_dias_vencidos_1 == 1
    assert respuesta.resumen.hoy.morosidad_monto == 200
    assert respuesta.resumen.hoy.morosidad_porcentaje == 10
    assert respuesta.agencia == "Ambato"
    assert respuesta.resumen.ayer is not None
    assert respuesta.resumen.ayer.saldo_capital == 1200
    assert respuesta.resumen.ayer.provision_requerida == 20
    assert respuesta.resumen.ayer.creditos_en_mora == 1
    assert respuesta.resumen.cambio is not None
    assert respuesta.resumen.cambio.saldo_capital == 800
    assert respuesta.resumen.cambio.provision_requerida == 80
    assert respuesta.resumen.cambio.morosidad_porcentaje == 3.33
    assert respuesta.asesores[0].asesor == "Ana"
    assert respuesta.asesores[0].hoy.saldo_capital == 2000
    assert respuesta.asesores[0].ayer is not None
    assert respuesta.asesores[0].ayer.saldo_capital == 0
    assert respuesta.asesores[0].cambio is not None
    assert respuesta.asesores[0].cambio.saldo_capital == 2000
    assert respuesta.asesores[1].asesor == "Carlos"
    assert respuesta.asesores[1].hoy.saldo_capital == 0
    assert respuesta.asesores[1].ayer is not None
    assert respuesta.asesores[1].ayer.saldo_capital == 1200
    assert respuesta.asesores[1].cambio is not None
    assert respuesta.asesores[1].cambio.saldo_capital == -1200


def test_resumen_cartera_usa_snapshots_actual_e_historico() -> None:
    auth_context = AuthContext(
        usuario=UsuarioTokenPayload(
            sub="ana",
            usuario="Ana",
            id_agencia=4,
            fecha_sistema=date(2026, 10, 5),
        ),
        token="token",
    )
    service = ResumenDiarioCarteraService(FakeSqlAgencyRepository(), FakeMongoRepository())

    respuesta = service.obtener(id_agencia=4, auth_context=auth_context)

    assert respuesta.resumen.hoy.saldo_capital == 2000
    assert respuesta.resumen.ayer is not None
    assert respuesta.asesores[0].ayer is not None


def test_repositorio_filtra_situacion_actual_por_id_agencia() -> None:
    class FakeCollection:
        def __init__(self) -> None:
            self.query = None

        def find(self, query, projection):
            self.query = query
            return []

    class FakeDatabase:
        def __init__(self) -> None:
            self.collections = {}

        def __getitem__(self, name):
            self.collections[name] = FakeCollection()
            return self.collections[name]

    database = FakeDatabase()
    repository = MongoResumenDiarioCarteraRepository(database)

    repository.obtener_snapshots_por_agencia(
        agencia="RIOBAMBA",
        fecha_corte_ayer="20261004",
    )

    filtro_hoy = database.collections["SituacionCrediticiaActual"].query
    filtro_ayer = database.collections["SituacionCrediticia"].query
    filtro_agencia = {"Agencia": "RIOBAMBA"}
    assert filtro_hoy == {
        "$and": [
            filtro_agencia,
            {"EstadoPrestamo": {"$ne": "CANCELADO"}},
        ]
    }
    assert filtro_ayer == {
        "$and": [
            filtro_agencia,
            {"EstadoPrestamo": {"$ne": "CANCELADO"}},
            {"fecha_corte": "20261004"},
        ]
    }
    assert set(database.collections) == {"SituacionCrediticiaActual", "SituacionCrediticia"}


def test_endpoint_expone_ayer_y_comparativa() -> None:
    app = FastAPI()
    app.include_router(negocios_router)
    app.dependency_overrides[get_current_auth_context] = lambda: AuthContext(
        usuario=UsuarioTokenPayload(
            sub="ana",
            usuario="Ana",
            id_agencia=4,
            fecha_sistema=date(2026, 10, 5),
        ),
        token="token",
    )
    app.dependency_overrides[get_resumen_diario_cartera_service] = lambda: (
        ResumenDiarioCarteraService(FakeSqlAgencyRepository(), FakeMongoRepository())
    )

    with TestClient(app) as client:
        response = client.get(
            "/negocios/cartera-de-credito/resumen-diario-asesores?id_agencia=4"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["agencia"] == "Ambato"
    assert body["resumen"]["ayer"]["saldo_capital"] == 1200
    assert body["resumen"]["cambio"]["saldo_capital"] == 800
    assert body["asesores"][0]["hoy"]["saldo_capital"] == 2000
    assert body["asesores"][0]["ayer"]["saldo_capital"] == 0
    assert body["asesores"][0]["cambio"]["saldo_capital"] == 2000

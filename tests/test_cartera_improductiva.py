from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.cartera_de_credito.cartera_improductiva.dependencies import (
    get_cartera_improductiva_service,
)
from app.modules.negocios.cartera_de_credito.cartera_improductiva.service import (
    CarteraImproductivaService,
)
from app.modules.negocios.router import router as negocios_router


def _document(
    numero: str,
    codigo: str,
    *,
    nombre: str,
    saldo: float,
    no_devenga: float,
    vencido: float,
    agencia: str = "CENTRO",
    diferido: bool = False,
) -> dict:
    return {
        "NumeroPrestamo": numero,
        "CodigoUsuario": codigo,
        "NombreAsesor": nombre,
        "CargoAsesor": "ASESOR DE NEGOCIOS",
        "Agencia": agencia,
        "Cliente": numero,
        "SaldoCapital": saldo,
        "CapitalNoDevenga": no_devenga,
        "CapitalVencido": vencido,
        "ProvisionRequerida": 0,
        "EstadoPrestamo": "VIGENTE",
        "EsDiferido": diferido,
    }


class FakeMongoRepository:
    def __init__(self) -> None:
        self.actuales = [
            _document(
                "1",
                "ASESOR_ACTUAL",
                nombre="Asesor actual",
                saldo=100,
                no_devenga=10,
                vencido=5,
            ),
            _document(
                "2",
                "SOLO_FIN",
                nombre="Solo final",
                saldo=50,
                no_devenga=2,
                vencido=3,
            ),
        ]
        self.historicos = {
            "20260920": [
                _document(
                    "1",
                    "ASESOR_ANTERIOR",
                    nombre="Asesor anterior",
                    saldo=50,
                    no_devenga=4,
                    vencido=6,
                )
            ],
            "20260922": [
                _document(
                    "1",
                    "ASESOR_ANTERIOR",
                    nombre="Asesor anterior",
                    saldo=40,
                    no_devenga=2,
                    vencido=2,
                )
            ],
        }

    def obtener_ultimo_corte_actual(self) -> str:
        return "20260923"

    def obtener_actual(
        self,
        fecha_corte: str,
        agencia_nombre: str | None,
    ) -> list[dict]:
        assert fecha_corte == "20260923"
        assert agencia_nombre is None
        return self.actuales

    def obtener_historico(
        self,
        fecha_corte: str,
        agencia_nombre: str | None,
    ) -> list[dict]:
        assert agencia_nombre is None
        return self.historicos[fecha_corte]


class FakeSqlRepository:
    def obtener_nombre_agencia(self, id_agencia: int) -> str | None:
        return "CENTRO" if id_agencia == 1 else None

    def obtener_gerentes_oficina(self, agencias: list[str]) -> list[dict]:
        assert agencias == ["CENTRO"]
        return [
            {
                "IdAgencia": 1,
                "Agencia": "CENTRO",
                "CodigoUsuarioGerente": "GERENTE",
                "GerenteOficina": "Gerente de oficina",
                "Cargo": "GERENTE DE OFICINA",
            }
        ]


def _service() -> CarteraImproductivaService:
    return CarteraImproductivaService(FakeMongoRepository(), FakeSqlRepository())


def test_service_compara_los_tres_cortes_y_reasigna_al_asesor_actual() -> None:
    response = _service().obtener(
        fecha_inicio=date(2026, 9, 20),
        fecha_fin=date(2026, 9, 23),
    )

    assert response.fecha_corte_fecha_fin == "20260923"
    assert response.fecha_corte_fecha_inicio == "20260920"
    assert response.fecha_corte_dia_anterior_fecha_fin == "20260922"
    assert [item.codigo_usuario for item in response.comparacion] == [
        "ASESOR_ACTUAL",
        "SOLO_FIN",
    ]

    asesor = response.comparacion[0]
    assert asesor.nombre_asesor_fecha_fin == "Asesor actual"
    assert asesor.nombre_asesor_fecha_inicio == "Asesor anterior"
    assert asesor.valores_fecha_fin is not None
    assert asesor.valores_fecha_fin.saldo_capital == 100
    assert asesor.valores_fecha_fin.cartera_improductiva == 15
    assert asesor.valores_fecha_fin.morosidad == 0.15
    assert asesor.valores_fecha_inicio is not None
    assert asesor.valores_fecha_inicio.saldo_capital == 50
    assert asesor.valores_fecha_inicio.cartera_improductiva == 10
    assert asesor.valores_fecha_inicio.morosidad_porcentaje == 20
    assert asesor.valores_dia_anterior_fecha_fin is not None
    assert asesor.valores_dia_anterior_fecha_fin.saldo_capital == 40
    assert asesor.valores_dia_anterior_fecha_fin.cartera_improductiva == 4
    assert response.faltantes_en_fecha_inicio == ["SOLO_FIN"]
    assert response.faltantes_en_dia_anterior_fecha_fin == ["SOLO_FIN"]
    assert response.agencias_gerentes_oficina[0].codigo_usuario_gerente == "GERENTE"


def test_service_aplica_el_filtro_de_diferidos_en_los_tres_cortes() -> None:
    mongo_repository = FakeMongoRepository()
    mongo_repository.actuales[1]["EsDiferido"] = True
    service = CarteraImproductivaService(mongo_repository, FakeSqlRepository())

    response = service.obtener(
        fecha_inicio=date(2026, 9, 20),
        fecha_fin=date(2026, 9, 23),
        filtrar_diferidos=False,
    )

    assert [item.codigo_usuario for item in response.comparacion] == ["ASESOR_ACTUAL"]
    assert response.faltantes_en_fecha_inicio == []
    assert response.faltantes_en_dia_anterior_fecha_fin == []


def test_service_permite_rangos_que_cruzan_meses() -> None:
    mongo_repository = FakeMongoRepository()
    mongo_repository.historicos["20260831"] = mongo_repository.historicos["20260920"]
    service = CarteraImproductivaService(mongo_repository, FakeSqlRepository())

    response = service.obtener(
        fecha_inicio=date(2026, 8, 31),
        fecha_fin=date(2026, 9, 23),
    )

    assert response.fecha_corte_fecha_inicio == "20260831"
    assert response.fecha_corte_dia_anterior_fecha_fin == "20260922"


def test_endpoint_expone_el_contrato_con_los_aliases() -> None:
    app = FastAPI()
    app.include_router(negocios_router)
    app.dependency_overrides[get_current_auth_context] = lambda: AuthContext(
        usuario=UsuarioTokenPayload(
            sub="ASESOR",
            usuario="ASESOR",
            id_agencia=1,
            fecha_sistema=date(2026, 9, 23),
        ),
        token="token",
    )
    app.dependency_overrides[get_cartera_improductiva_service] = _service

    with TestClient(app) as client:
        response = client.post(
            "/negocios/cartera-de-credito/cartera-improductiva",
            json={
                "fecha_inicio": "2026-09-20",
                "fecha_fin": "2026-09-23",
                "id_agencia": 0,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["fecha_corte_fecha_fin"] == "20260923"
    assert body["comparacion"][0]["ValoresFechaFin"] == {
        "SaldoCapital": 100.0,
        "CarteraImproductiva": 15.0,
        "Morosidad": 0.15,
        "MorosidadPorcentaje": 15.0,
    }


def test_service_filtra_la_agencia_en_los_tres_cortes() -> None:
    class MongoPorAgencia(FakeMongoRepository):
        def obtener_actual(self, fecha_corte, agencia_nombre):
            assert fecha_corte == "20260923"
            assert agencia_nombre == "CENTRO"
            return [item for item in self.actuales if item["Agencia"] == agencia_nombre]

        def obtener_historico(self, fecha_corte, agencia_nombre):
            assert agencia_nombre == "CENTRO"
            return [
                item for item in self.historicos[fecha_corte]
                if item["Agencia"] == agencia_nombre
            ]

    mongo = MongoPorAgencia()
    otra_agencia = _document(
        "3", "OTRO", nombre="Otro asesor", saldo=900,
        no_devenga=0, vencido=0, agencia="QUITO",
    )
    mongo.actuales.append(otra_agencia)
    for documentos in mongo.historicos.values():
        documentos.append(otra_agencia)
    service = CarteraImproductivaService(mongo, FakeSqlRepository())

    response = service.obtener(
        fecha_inicio=date(2026, 9, 20),
        fecha_fin=date(2026, 9, 23),
        id_agencia=1,
    )

    assert [item.codigo_usuario for item in response.comparacion] == [
        "ASESOR_ACTUAL", "SOLO_FIN",
    ]
    assert sum(item.valores_fecha_fin.saldo_capital for item in response.comparacion) == 150
    assert response.comparacion[0].valores_fecha_inicio.saldo_capital == 50
    assert response.comparacion[0].valores_dia_anterior_fecha_fin.saldo_capital == 40

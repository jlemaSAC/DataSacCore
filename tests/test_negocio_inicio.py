from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.schemas import (
    AsesorCarteraComparativo,
    CarteraIndicadores,
    ResumenCarteraComparativo,
    ResumenDiarioCarteraAsesoresResponse,
)
from app.modules.negocios.colocacion.diaria_asesores.schemas import (
    ColocacionAsesorComparativo,
    ColocacionDiariaAsesoresResponse,
    ColocacionIndicadores,
    ColocacionResumenComparativo,
)
from app.modules.negocios.inicio.dependencies import get_negocio_inicio_service
from app.modules.negocios.inicio.service import NegocioInicioService
from app.modules.negocios.router import router as negocios_router


class FakeColocacionService:
    def obtener(self, *, id_agencia: int, auth_context: AuthContext):
        assert id_agencia == 4
        return ColocacionDiariaAsesoresResponse(
            fecha=date(2026, 10, 5),
            fecha_ayer=date(2026, 10, 4),
            id_agencia=4,
            agencia="Ambato",
            resumen=ColocacionResumenComparativo(
                hoy=ColocacionIndicadores(operaciones=2, monto_colocado=1000),
                ayer=ColocacionIndicadores(operaciones=1, monto_colocado=400),
                cambio=ColocacionIndicadores(operaciones=1, monto_colocado=600),
            ),
            asesores=[
                ColocacionAsesorComparativo(
                    codigo_usuario="ana",
                    asesor="Ana",
                    hoy=ColocacionIndicadores(operaciones=2, monto_colocado=1000),
                    ayer=ColocacionIndicadores(operaciones=1, monto_colocado=400),
                    cambio=ColocacionIndicadores(operaciones=1, monto_colocado=600),
                )
            ],
        )


class FakeCarteraService:
    def obtener(self, *, id_agencia: int, auth_context: AuthContext):
        assert id_agencia == 4
        return ResumenDiarioCarteraAsesoresResponse(
            fecha=date(2026, 10, 5),
            fecha_ayer=date(2026, 10, 4),
            id_agencia=id_agencia,
            agencia="Ambato",
            resumen=ResumenCarteraComparativo(
                hoy=CarteraIndicadores(
                    operaciones=10,
                    creditos_en_mora=2,
                    creditos_dias_vencidos_1=1,
                    saldo_capital=25000,
                    provision_requerida=200,
                    morosidad_monto=500,
                    morosidad_porcentaje=2,
                ),
                ayer=CarteraIndicadores(
                    operaciones=9,
                    creditos_en_mora=1,
                    creditos_dias_vencidos_1=0,
                    saldo_capital=24000,
                    provision_requerida=180,
                    morosidad_monto=300,
                    morosidad_porcentaje=1.25,
                ),
                cambio=CarteraIndicadores(
                    operaciones=1,
                    creditos_en_mora=1,
                    creditos_dias_vencidos_1=1,
                    saldo_capital=1000,
                    provision_requerida=20,
                    morosidad_monto=200,
                    morosidad_porcentaje=0.75,
                ),
            ),
            asesores=[
                AsesorCarteraComparativo(
                    codigo_usuario="ana",
                    asesor="Ana",
                    hoy=CarteraIndicadores(
                        operaciones=4,
                        creditos_en_mora=1,
                        creditos_dias_vencidos_1=1,
                        saldo_capital=10000,
                        provision_requerida=100,
                        morosidad_monto=300,
                        morosidad_porcentaje=3,
                    ),
                    ayer=CarteraIndicadores(
                        operaciones=3,
                        creditos_en_mora=0,
                        creditos_dias_vencidos_1=0,
                        saldo_capital=9000,
                        provision_requerida=90,
                        morosidad_monto=100,
                        morosidad_porcentaje=1.11,
                    ),
                    cambio=CarteraIndicadores(
                        operaciones=1,
                        creditos_en_mora=1,
                        creditos_dias_vencidos_1=1,
                        saldo_capital=1000,
                        provision_requerida=10,
                        morosidad_monto=200,
                        morosidad_porcentaje=1.89,
                    ),
                )
            ],
        )


def test_endpoint_inicio_unifica_colocacion_y_cartera() -> None:
    auth_context = AuthContext(
        usuario=UsuarioTokenPayload(
            sub="ana",
            usuario="Ana",
            id_agencia=4,
            fecha_sistema=date(2026, 10, 5),
        ),
        token="token",
    )
    service = NegocioInicioService(FakeColocacionService(), FakeCarteraService())
    app = FastAPI()
    app.include_router(negocios_router)
    app.dependency_overrides[get_current_auth_context] = lambda: auth_context
    app.dependency_overrides[get_negocio_inicio_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/negocios/inicio?id_agencia=4")

    assert response.status_code == 200
    body = response.json()
    assert body["fecha"] == "2026-10-05"
    assert body["agencia"] == "Ambato"
    assert body["colocacion"]["resumen"]["cambio"]["monto_colocado"] == 600
    assert body["colocacion"]["asesores"][0]["codigo_usuario"] == "ana"
    assert body["cartera_de_credito"]["resumen"]["hoy"]["saldo_capital"] == 25000
    assert body["cartera_de_credito"]["asesores"][0]["cambio"]["creditos_en_mora"] == 1

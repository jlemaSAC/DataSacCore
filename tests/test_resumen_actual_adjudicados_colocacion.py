from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.colocacion.colocacion_historico.domain import (
    ColocacionAgrupada,
    DimensionesColocacion,
    PrestamoAdjudicado,
    TotalesResumenColocacion,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.colocacion.resumen.dependencies import get_resumen_colocacion_service
from app.modules.negocios.colocacion.resumen.schemas import InputResumenActualColocacion
from app.modules.negocios.colocacion.resumen.service import ResumenColocacionService


def _auth_context() -> AuthContext:
    return AuthContext.from_token_payload(
        "token",
        UsuarioTokenPayload(
            sub="jdoe",
            usuario="John Doe",
            id_agencia=2,
            nombre_agencia="Matriz",
            fecha_sistema=date(2026, 8, 31),
        ),
    )


def _agrupacion(operaciones: int, saldo: float) -> ColocacionAgrupada:
    dimensiones = DimensionesColocacion(
        periodo="2026-08",
        anio=2026,
        mes=8,
        agencia="MATRIZ",
        condicion="NUEVO",
        tipo_prestamo="ORDINARIO",
        producto="MICROCREDITO",
        segmento="MINORISTA",
        asesor="JUAN PEREZ",
        provincia="SIN DATOS",
        canton="SIN DATOS",
        parroquia="SIN DATOS",
        educacion="SIN DATOS",
        edad="SIN DATOS",
        garantia="SIN DATOS",
        monto="SIN DATOS",
        tasa="SIN DATOS",
        tasa_valor=16.0,
        tasa_real="SIN DATOS",
        tasa_real_valor=17.0,
        plazo="SIN DATOS",
        plazo_valor=None,
    )
    return ColocacionAgrupada(dimensiones, operaciones, saldo)


class _FakeColocacionHistoricoService:
    def __init__(self) -> None:
        self.filtro_prestamos: list[str] | None = None
        self.llamadas_agrupaciones: list[tuple[date, date, list[str]]] = []
        self.llamadas_totales: list[tuple[dict[str, tuple[date, date]], list[str]]] = []

    def obtener_agrupaciones_resumen_por_rango(
        self, fecha_inicio, fecha_fin, _fecha_hoy, agencias
    ):
        self.llamadas_agrupaciones.append((fecha_inicio, fecha_fin, agencias))
        datos = {
            (date(2026, 1, 1), date(2026, 8, 25)): _agrupacion(20, 2000.0),
            (date(2026, 8, 15), date(2026, 8, 25)): _agrupacion(10, 1000.0),
            (date(2026, 7, 1), date(2026, 7, 31)): _agrupacion(30, 3000.0),
            (date(2025, 1, 1), date(2025, 12, 31)): _agrupacion(40, 4000.0),
        }
        fila = datos.get((fecha_inicio, fecha_fin))
        return {fila.dimensiones: fila} if fila else {}

    def obtener_totales_resumen_por_rangos(self, rangos, _fecha_hoy, agencias):
        self.llamadas_totales.append((rangos, agencias))
        datos = {
            "acumulado_anual": TotalesResumenColocacion(
                operaciones=20,
                saldo_inicial=2000.0,
                suma_tasa_nominal=320.0,
                operaciones_tasa_nominal=20,
                suma_tasa_real=340.0,
                operaciones_tasa_real=20,
            ),
            "actual": TotalesResumenColocacion(
                operaciones=10,
                saldo_inicial=1000.0,
                suma_tasa_nominal=160.0,
                operaciones_tasa_nominal=10,
                suma_tasa_real=170.0,
                operaciones_tasa_real=10,
            ),
            "mes_anterior": TotalesResumenColocacion(
                operaciones=30,
                saldo_inicial=3000.0,
            ),
            "anio_anterior": TotalesResumenColocacion(
                operaciones=40,
                saldo_inicial=4000.0,
            ),
        }
        return datos

    def obtener_prestamos_adjudicados_resumen_por_rango(
        self, fecha_inicio, fecha_fin, fecha_hoy, agencias
    ):
        assert (fecha_inicio, fecha_fin, fecha_hoy) == (
            date(2026, 8, 15),
            date(2026, 8, 25),
            date(2026, 8, 31),
        )
        self.filtro_prestamos = agencias
        return [
            PrestamoAdjudicado(
                numero_operacion="2026081703165",
                producto="MICROCREDITO",
                valor=1000.0,
                agencia="MATRIZ",
                tipo_prestamo="ORDINARIO",
                asesor="JUAN PEREZ",
                fecha_adjudicacion=date(2026, 8, 17),
            )
        ]


def test_resumen_actual_con_adjudicados_retorna_el_detalle_directamente() -> None:
    service = ResumenColocacionService(_FakeColocacionHistoricoService())  # type: ignore[arg-type]

    respuesta = service.obtener_resumen_actual_con_adjudicados(
        InputResumenActualColocacion(
            fecha_inicio=date(2026, 8, 15),
            fecha_fin=date(2026, 8, 25),
        ),
        _auth_context(),
    )

    assert respuesta.actual.colocacion_general == 1000.0
    assert respuesta.mes_anterior.colocacion_general == 3000.0
    assert respuesta.anio_anterior.colocacion_general == 4000.0
    assert respuesta.model_dump()["prestamos_adjudicados"] == [
        {
            "producto": "MICROCREDITO",
            "valor": 1000.0,
            "agencia": "MATRIZ",
            "tipo_prestamo": "ORDINARIO",
            "asesor": "JUAN PEREZ",
            "fecha_adjudicacion": date(2026, 8, 17),
        }
    ]


def test_resumen_actual_con_adjudicados_aplica_el_filtro_de_agencias() -> None:
    historico = _FakeColocacionHistoricoService()
    service = ResumenColocacionService(historico)  # type: ignore[arg-type]

    service.obtener_resumen_actual_con_adjudicados(
        InputResumenActualColocacion(
            fecha_inicio=date(2026, 8, 15),
            fecha_fin=date(2026, 8, 25),
            agencias=["MATRIZ"],
        ),
        _auth_context(),
    )

    assert historico.filtro_prestamos == ["MATRIZ"]
    assert historico.llamadas_agrupaciones == []
    assert historico.llamadas_totales == [
        (
            {
                "acumulado_anual": (date(2026, 1, 1), date(2026, 8, 25)),
                "actual": (date(2026, 8, 15), date(2026, 8, 25)),
                "mes_anterior": (date(2026, 7, 1), date(2026, 7, 31)),
                "anio_anterior": (date(2025, 1, 1), date(2025, 12, 31)),
            },
            ["MATRIZ"],
        )
    ]


def test_resumen_actual_existente_conserva_colocacion_por_agencia() -> None:
    historico = _FakeColocacionHistoricoService()
    service = ResumenColocacionService(historico)  # type: ignore[arg-type]

    respuesta = service.obtener_resumen_actual(
        InputResumenActualColocacion(
            fecha_inicio=date(2026, 8, 15),
            fecha_fin=date(2026, 8, 25),
        ),
        _auth_context(),
    )

    assert respuesta.colocacion_por_agencia[0].agencia == "MATRIZ"
    assert historico.llamadas_agrupaciones == [
        (date(2026, 8, 15), date(2026, 8, 25), [])
    ]


def test_endpoint_resumen_actual_adjudicados_retorna_detalle_por_agencia() -> None:
    service = ResumenColocacionService(_FakeColocacionHistoricoService())  # type: ignore[arg-type]
    app.dependency_overrides[get_current_auth_context] = _auth_context
    app.dependency_overrides[get_resumen_colocacion_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/negocios/colocacion/resumen-actual-adjudicados",
            json={"fecha_inicio": "2026-08-15", "fecha_fin": "2026-08-25"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["prestamos_adjudicados"] == [
        {
            "producto": "MICROCREDITO",
            "valor": 1000.0,
            "agencia": "MATRIZ",
            "tipo_prestamo": "ORDINARIO",
            "asesor": "JUAN PEREZ",
            "fecha_adjudicacion": "2026-08-17",
        }
    ]

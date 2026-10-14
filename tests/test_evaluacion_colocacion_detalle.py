from datetime import date

import pytest
from pydantic import ValidationError

from app.modules.analytic.colocacion.colocacion_historico.domain import (
    DetalleColocacion,
    ResultadoDetalleColocacion,
)
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.colocacion.resumen.schemas import InputDetalleResumenColocacion
from app.modules.negocios.colocacion.resumen.service import ResumenColocacionService


def _auth_context() -> AuthContext:
    return AuthContext.from_token_payload(
        "token",
        UsuarioTokenPayload(
            sub="jdoe",
            usuario="John Doe",
            id_agencia=1,
            nombre_agencia="Matriz",
            fecha_sistema=date(2026, 8, 31),
        ),
    )


class _FakeColocacionHistoricoService:
    def __init__(self) -> None:
        self.parametros: dict | None = None

    def obtener_detalles_resumen_por_rango(self, **kwargs) -> ResultadoDetalleColocacion:
        self.parametros = kwargs
        return ResultadoDetalleColocacion(
            items=[
                DetalleColocacion(
                    numero_cliente="1",
                    nombre_cliente="CLIENTE",
                    numero_operacion="123",
                    agencia="MATRIZ",
                    asesor="ANA ASESORA",
                    tipo_condicion="NUEVO",
                    producto="MICROCREDITO",
                    tipo_prestamo="ORDINARIO",
                    segmento="MINORISTA",
                    tasa_nominal=16.0,
                    tasa_real=17.0,
                    monto_colocado=100.0,
                )
            ],
            total_registros=1,
            total_monto_colocado=100.0,
        )


def _input(**overrides) -> InputDetalleResumenColocacion:
    return InputDetalleResumenColocacion(
        agencias=["MATRIZ"],
        fecha_inicio=date(2026, 8, 1),
        fecha_fin=date(2026, 8, 31),
        dimension="producto",
        valor_dimension="MICROCREDITO",
        **overrides,
    )


def test_detalle_propaga_condiciones_normalizadas_al_hecho_historico() -> None:
    historico = _FakeColocacionHistoricoService()
    respuesta = ResumenColocacionService(historico).obtener_detalle(  # type: ignore[arg-type]
        _input(condiciones=[" nuevo ", "NUEVO"]),
        _auth_context(),
    )

    assert historico.parametros is not None
    assert historico.parametros["condiciones"] == ["NUEVO"]
    assert respuesta.total_registros == 1


def test_detalle_rechaza_condiciones_vacias() -> None:
    with pytest.raises(ValidationError, match="condiciones no puede contener nombres vacíos"):
        _input(condiciones=["   "])

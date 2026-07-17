import logging
from datetime import datetime
from time import perf_counter

from fastapi import HTTPException

from app.modules.analytic.recuperacion.recuperacion_historico.domain import (
    PrestamoRecuperacion,
    RecuperacionEtiquetada,
)
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.mongo_recuperacion_historico_repository import (
    MongoRecuperacionHistoricoRepository,
)
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.sql_recuperacion_historico_repository import (
    SqlRecuperacionHistoricoRepository,
)
from app.modules.analytic.recuperacion.recuperacion_historico.schemas import (
    InputRecuperacionHistoricoRango,
    RecuperacionEtiquetadaOut,
    RecuperacionHistoricoRangoResponse,
    PrestamoRecuperacionOut,
)
from app.modules.auth.schemas import AuthContext


logger = logging.getLogger("uvicorn.error")
MAX_MESES_RANGO = 60


class RecuperacionHistoricoService:
    def __init__(
        self,
        mongo_repository: MongoRecuperacionHistoricoRepository,
        sql_repository: SqlRecuperacionHistoricoRepository | None = None,
    ) -> None:
        self.mongo_repository = mongo_repository
        self.sql_repository = sql_repository

    def obtener_recuperacion_por_rango(
        self,
        input_data: InputRecuperacionHistoricoRango,
        auth_context: AuthContext,
    ) -> RecuperacionHistoricoRangoResponse:
        try:
            fecha_sistema = auth_context.usuario.fecha_sistema
            fecha_hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
            if input_data.fecha_hasta > fecha_hoy:
                raise HTTPException(400, "fecha_hasta no puede ser posterior a la fecha del sistema.")
            meses = (input_data.fecha_hasta.year - input_data.fecha_desde.year) * 12 + input_data.fecha_hasta.month - input_data.fecha_desde.month + 1
            if meses > MAX_MESES_RANGO:
                raise HTTPException(400, f"El rango no puede superar {MAX_MESES_RANGO} meses.")

            inicio_mongo = perf_counter()
            recuperaciones = self.mongo_repository.obtener_recuperaciones(input_data, fecha_hoy)
            print(f"[recuperacion][service] mongo_total_ms={(perf_counter() - inicio_mongo) * 1000:.2f}")
            inicio_prestamos = perf_counter()
            numeros_prestamo = {
                recuperacion.numero_prestamo
                for recuperacion in recuperaciones
                if recuperacion.numero_prestamo
            }
            prestamos_por_numero = self.mongo_repository.obtener_prestamos_por_numero(
                numeros_prestamo,
                input_data.fecha_desde.strftime("%Y%m%d"),
                input_data.fecha_hasta.strftime("%Y%m%d"),
                fecha_hoy.strftime("%Y%m%d"),
            )
            print(
                "[recuperacion][service] prestamos_total_ms="
                f"{(perf_counter() - inicio_prestamos) * 1000:.2f} prestamos={len(prestamos_por_numero)}"
            )
            inicio_respuesta = perf_counter()
            respuesta = self._construir_respuesta(input_data, recuperaciones, prestamos_por_numero)
            print(
                "[recuperacion][service] respuesta_ms="
                f"{(perf_counter() - inicio_respuesta) * 1000:.2f} recuperaciones={len(recuperaciones)}"
            )
            return respuesta
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error consultando recuperacion en Mongo")
            raise HTTPException(status_code=500, detail=f"Error consultando recuperacion: {exc}") from exc

    @staticmethod
    def _construir_respuesta(
        input_data: InputRecuperacionHistoricoRango,
        recuperaciones: list[RecuperacionEtiquetada],
        prestamos_por_numero: dict[str, PrestamoRecuperacion],
    ) -> RecuperacionHistoricoRangoResponse:
        datos: list[RecuperacionEtiquetadaOut] = []
        for recuperacion in recuperaciones:
            prestamo_actual = prestamos_por_numero.get(recuperacion.numero_prestamo)
            datos.append(RecuperacionEtiquetadaOut(
                anio=recuperacion.fecha_cobro.year,
                mes=recuperacion.fecha_cobro.month,
                numero_prestamo=recuperacion.numero_prestamo,
                tipo_cobro=recuperacion.tipo_cobro,
                tipo_transaccion=recuperacion.tipo_transaccion,
                valor_recuperado=recuperacion.valor_recuperado,
                agencia=_valor_contexto(recuperacion.agencia, prestamo_actual, "agencia"),
                asesor=_valor_contexto(recuperacion.asesor, prestamo_actual, "asesor"),
                abogado_externo=recuperacion.abogado_externo,
                nombre_cobranza_apoyo=recuperacion.nombre_cobranza_apoyo,
                estado_prestamo_anterior_cobro=_valor_contexto(
                    recuperacion.estado_prestamo_anterior_cobro,
                    prestamo_actual,
                    "estado_prestamo_inicio",
                ),
                estado_prestamo_actual_cobro=_valor_contexto(
                    recuperacion.estado_prestamo_actual_cobro,
                    prestamo_actual,
                    "estado_prestamo_fin",
                ),
                calificacion_anterior_cobro=_valor_contexto(
                    recuperacion.calificacion_anterior_cobro,
                    prestamo_actual,
                    "calificacion_inicio",
                ),
                calificacion_actual_cobro=_valor_contexto(
                    recuperacion.calificacion_actual_cobro,
                    prestamo_actual,
                    "calificacion_fin",
                ),
                se_cancelo_con_el_cobro=recuperacion.se_cancelo_con_el_cobro,
            ))

        return RecuperacionHistoricoRangoResponse(
            prestamos_por_numero={
                numero: PrestamoRecuperacionOut(**prestamo.__dict__)
                for numero, prestamo in prestamos_por_numero.items()
            },
            recuperaciones=datos,
        )


def _valor_contexto(
    valor: str,
    prestamo: PrestamoRecuperacion | None,
    atributo: str,
) -> str:
    if valor != "SIN DATOS" or prestamo is None:
        return valor
    return str(getattr(prestamo, atributo) or "SIN DATOS")

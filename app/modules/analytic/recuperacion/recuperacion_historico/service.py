import calendar
import logging
from datetime import date, datetime
from time import perf_counter

from fastapi import HTTPException

from app.modules.analytic.recuperacion.recuperacion_historico.domain import (
    PrestamoRecuperacion,
    RecuperacionEtiquetada,
)
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.mongo_recuperacion_historico_repository import (
    MongoRecuperacionHistoricoRepository,
    _prestamo_desde_situacion,
)
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.sql_recuperacion_historico_repository import (
    SqlRecuperacionHistoricoRepository,
)
from app.modules.analytic.recuperacion.recuperacion_historico.schemas import (
    InputRecuperacionHistoricoRango,
    RecuperacionEtiquetadaOut,
    RecuperacionHistoricoRangoResponse,
    PrestamoRecuperacionOut,
    ResumenMensualRecuperacion,
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
            if input_data.fecha_hasta == fecha_hoy:
                if self.sql_repository is None:
                    raise RuntimeError("Repositorio SQL no configurado para el corte actual.")
                prestamos_por_numero = {
                    numero: _prestamo_desde_situacion(
                        numero,
                        documento,
                        str(documento.get("EstadoPrestamo") or "SIN DATOS"),
                    )
                    for numero, documento in self.sql_repository.obtener_prestamos_actuales(
                        numeros_prestamo
                    ).items()
                }
            else:
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
        totales_mes: dict[str, float] = {}
        datos: list[RecuperacionEtiquetadaOut] = []
        for recuperacion in recuperaciones:
            periodo = recuperacion.fecha_cobro.strftime("%Y-%m")
            totales_mes[periodo] = totales_mes.get(periodo, 0.0) + recuperacion.valor_recuperado
            prestamo_actual = prestamos_por_numero.get(recuperacion.numero_prestamo)
            datos.append(RecuperacionEtiquetadaOut(
                fecha_cobro=recuperacion.fecha_cobro,
                periodo=periodo,
                anio=recuperacion.fecha_cobro.year,
                mes=recuperacion.fecha_cobro.month,
                numero_prestamo=recuperacion.numero_prestamo,
                tipo_cobro=recuperacion.tipo_cobro,
                tipo_transaccion=recuperacion.tipo_transaccion,
                valor_recuperado=recuperacion.valor_recuperado,
                agencia=_valor_contexto(recuperacion.agencia, prestamo_actual, "agencia"),
                asesor=_valor_contexto(recuperacion.asesor, prestamo_actual, "asesor"),
                abogado_externo=recuperacion.abogado_externo,
                codigo_cobranza_apoyo=recuperacion.codigo_cobranza_apoyo,
                nombre_cobranza_apoyo=recuperacion.nombre_cobranza_apoyo,
                estado_prestamo_cobro=_valor_contexto(
                    recuperacion.estado_prestamo_cobro,
                    prestamo_actual,
                    "estado_prestamo_fin",
                ),
                calificacion_cobro=recuperacion.calificacion_cobro,
                fecha_estado_prestamo_anterior_cobro=(
                    recuperacion.fecha_estado_prestamo_anterior_cobro
                ),
                estado_prestamo_anterior_cobro=recuperacion.estado_prestamo_anterior_cobro,
                fecha_estado_prestamo_actual_cobro=(
                    recuperacion.fecha_estado_prestamo_actual_cobro
                ),
                estado_prestamo_actual_cobro=recuperacion.estado_prestamo_actual_cobro,
                calificacion_anterior_cobro=recuperacion.calificacion_anterior_cobro,
                calificacion_actual_cobro=recuperacion.calificacion_actual_cobro,
                es_cancelado_anterior_cobro=recuperacion.es_cancelado_anterior_cobro,
                es_cancelado_actual_cobro=recuperacion.es_cancelado_actual_cobro,
                se_cancelo_con_el_cobro=recuperacion.se_cancelo_con_el_cobro,
            ))

        resumen: list[ResumenMensualRecuperacion] = []
        cursor = date(input_data.fecha_desde.year, input_data.fecha_desde.month, 1)
        while cursor <= input_data.fecha_hasta:
            periodo = cursor.strftime("%Y-%m")
            ultimo_dia = calendar.monthrange(cursor.year, cursor.month)[1]
            resumen.append(ResumenMensualRecuperacion(
                periodo=periodo,
                anio=cursor.year,
                mes=cursor.month,
                fecha_desde=max(input_data.fecha_desde, cursor),
                fecha_hasta=min(input_data.fecha_hasta, date(cursor.year, cursor.month, ultimo_dia)),
                total_recuperado=totales_mes.get(periodo, 0.0),
            ))
            cursor = date(cursor.year + 1, 1, 1) if cursor.month == 12 else date(cursor.year, cursor.month + 1, 1)
        return RecuperacionHistoricoRangoResponse(
            fecha_desde=input_data.fecha_desde,
            fecha_hasta=input_data.fecha_hasta,
            total_recuperado=sum(totales_mes.values()),
            resumen_mensual=resumen,
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

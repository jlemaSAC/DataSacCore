import logging
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.recuperacion.recaudacion_acumulada.domain import (
    DetalleCuotaPrestamo,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.repositories.mongo_recaudacion_acumulada_repository import (
    MongoRecaudacionAcumuladaRepository,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.repositories.sql_detalle_cuotas_repository import (
    SqlDetalleCuotasRepository,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.repositories.sql_asesores_agencia_repository import (
    SqlAsesoresAgenciaRepository,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.schemas import (
    AsesorAgenciaResponse,
    GaranteRecaudacion,
    InformacionPersonaRecaudacion,
    InputRecaudacionAcumulada,
    PrestamoRecaudadoAcumulado,
    RecaudacionAcumuladaResponse,
)


logger = logging.getLogger("uvicorn.error")


class AsesoresAgenciaService:
    def __init__(self, repository: SqlAsesoresAgenciaRepository) -> None:
        self.repository = repository

    def listar(self, ids_agencia: list[int]) -> list[AsesorAgenciaResponse]:
        return [
            AsesorAgenciaResponse(**asesor._asdict())
            for asesor in self.repository.listar(ids_agencia)
        ]


class RecaudacionAcumuladaService:
    def __init__(
        self,
        mongo_repository: MongoRecaudacionAcumuladaRepository,
        sql_repository: SqlDetalleCuotasRepository,
    ) -> None:
        self.mongo_repository = mongo_repository
        self.sql_repository = sql_repository

    def obtener_recaudacion_acumulada(
        self,
        input_data: InputRecaudacionAcumulada,
        auth_context: AuthContext,
    ) -> RecaudacionAcumuladaResponse:
        fecha_sistema = auth_context.usuario.fecha_sistema
        fecha_actual = (
            fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        )
        if input_data.fecha_fin > fecha_actual:
            raise HTTPException(
                status_code=400,
                detail="fecha_fin no puede ser posterior a la fecha del sistema.",
            )

        try:
            fecha_cierre_anterior = _cierre_mes_anterior(input_data.fecha_inicio)
            for fecha_corte in (fecha_cierre_anterior, input_data.fecha_fin):
                if not self.mongo_repository.existe_corte(fecha_corte, fecha_actual):
                    raise HTTPException(
                        status_code=404,
                        detail=(
                            "No existe información de situación crediticia para "
                            f"el corte {fecha_corte.isoformat()}."
                        ),
                    )
            corte_final = self.mongo_repository.obtener_corte_final(
                fecha_corte=input_data.fecha_fin,
                fecha_actual=fecha_actual,
                agencias=input_data.agencias,
                asesores=input_data.asesores,
            )
            corte_inicial = self.mongo_repository.obtener_corte_inicial(
                fecha_cierre_anterior,
                list(corte_final),
            )

            numeros = sorted(
                numero
                for numero, fin in corte_final.items()
                if not _es_cancelado(fin) or numero in corte_inicial
            )
            recuperaciones = self.mongo_repository.obtener_recuperaciones(
                fecha_inicio=input_data.fecha_inicio,
                fecha_fin=input_data.fecha_fin,
                fecha_actual=fecha_actual,
                numeros_prestamo=numeros,
            )
            payload_sql = [
                {
                    "numero_prestamo": numero,
                    "provision_actual": _a_float(
                        corte_final[numero].get("ProvisionRequerida")
                    ),
                    "saldo_actual": _a_float(
                        corte_final[numero].get("SaldoCapital")
                    ),
                }
                for numero in numeros
            ]
            detalles = self.sql_repository.obtener_detalles(payload_sql)
            items = [
                self._construir_item(
                    numero=numero,
                    inicio=corte_inicial.get(numero, {}),
                    fin=corte_final[numero],
                    detalle=detalles.get(numero),
                    total_recuperado=(
                        recuperaciones[numero].total_recuperado
                        if numero in recuperaciones
                        else 0.0
                    ),
                    fecha_ultimo_pago=(
                        recuperaciones[numero].fecha_ultimo_pago
                        if numero in recuperaciones
                        else None
                    ),
                )
                for numero in numeros
            ]
            items.sort(key=lambda item: (-item.total_recuperado, item.numero_prestamo))
            return RecaudacionAcumuladaResponse(
                fecha_inicio=input_data.fecha_inicio,
                fecha_fin=input_data.fecha_fin,
                total_registros=len(items),
                total_recuperado=round(sum(item.total_recuperado for item in items), 2),
                prestamos=items,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error consultando recaudación acumulada")
            raise HTTPException(
                status_code=500,
                detail="Error consultando recaudación acumulada.",
            ) from exc

    @staticmethod
    def _construir_item(
        *,
        numero: str,
        inicio: dict[str, Any],
        fin: dict[str, Any],
        detalle: DetalleCuotaPrestamo | None,
        total_recuperado: float,
        fecha_ultimo_pago: date | None,
    ) -> PrestamoRecaudadoAcumulado:
        detalle = detalle or DetalleCuotaPrestamo(numero_prestamo=numero)
        personal = fin if fin.get("Nombres") else inicio
        estado_anterior = _texto(inicio.get("EstadoPrestamo"), "NO EXISTIA")
        estado_actual = _texto(fin.get("EstadoPrestamo"), "SIN DATOS")
        calificacion_anterior = _texto(inicio.get("Calificacion"), "NO EXISTIA")
        calificacion_actual = _texto(fin.get("Calificacion"), "SIN DATOS")
        dias_mora_anterior = _a_int(inicio.get("DiasVencidos"))
        dias_mora_actual = _a_int(fin.get("DiasVencidos"))
        saldo_anterior = _a_float(inicio.get("SaldoCapital"))
        saldo_actual = _a_float(fin.get("SaldoCapital"))
        provision_anterior = _a_float(inicio.get("ProvisionRequerida"))
        provision_actual = _a_float(fin.get("ProvisionRequerida"))
        cancelado = _es_cancelado(fin)

        informacion_deudor = None
        garante_1 = None
        garante_2 = None
        if not cancelado:
            informacion_deudor = InformacionPersonaRecaudacion(
                identificacion=_texto(
                    personal.get("Identificacion"), detalle.identificacion
                ),
                provincia=_texto(personal.get("Provincia"), detalle.provincia),
                canton=_texto(personal.get("Canton"), detalle.canton),
                parroquia=_texto(personal.get("Parroquia"), detalle.parroquia),
                direccion=_texto(personal.get("Direccion"), detalle.direccion),
                telefonos=_texto(personal.get("Telefonos"), detalle.telefonos),
            )
            garante_1 = _construir_garante(personal, "G1_", detalle.garante_1)
            garante_2 = _construir_garante(personal, "G2_", detalle.garante_2)

        provision_simulada = _calcular_provision_simulada(
            detalle=detalle,
            provision_actual=provision_actual,
            saldo_actual=saldo_actual,
        )
        return PrestamoRecaudadoAcumulado(
            socio=_a_int_opcional(personal.get("Cliente")) or detalle.socio,
            agencia=_texto(fin.get("Agencia")),
            numero_prestamo=numero,
            codigo_usuario_asignado=_texto(fin.get("CodigoAsesor")),
            nombre_usuario_asignado=_texto(fin.get("NombreAsesor"), "SIN ASESOR"),
            nombre=_texto(personal.get("Nombres"), detalle.nombre),
            estado_anterior=estado_anterior,
            estado_actual=estado_actual,
            calificacion_anterior=calificacion_anterior,
            calificacion_actual=calificacion_actual,
            dias_mora_anterior=dias_mora_anterior,
            dias_mora_actual=dias_mora_actual,
            variacion_dias_mora=dias_mora_actual - dias_mora_anterior,
            saldo_capital_anterior=round(saldo_anterior, 2),
            saldo_capital_actual=round(saldo_actual, 2),
            variacion_saldo_capital=round(saldo_actual - saldo_anterior, 2),
            numero_cuota_actual_no_pagada=detalle.numero_cuota_actual_no_pagada,
            numero_cuota_siguiente=detalle.numero_cuota_siguiente,
            cobro_para_bajar_una_cuota=round(detalle.cobro_hasta_cuota, 2),
            cuotas_pendientes=detalle.cuotas_pendientes,
            cuotas_pagadas=detalle.cuotas_pagadas,
            total_cuotas=detalle.total_cuotas or _a_int(fin.get("Plazo")),
            calificacion_con_cobro_una_cuota=(
                detalle.calificacion_con_cobro_una_cuota
            ),
            dias_mora_con_cobro_una_cuota=(
                detalle.dias_mora_con_cobro_una_cuota
            ),
            saldo_capital_con_cobro_una_cuota=round(
                detalle.saldo_capital_con_cobro_una_cuota, 2
            ),
            provision_con_cobro_una_cuota=provision_simulada,
            provision_cierre_mes=round(provision_anterior, 2),
            provision_actual=round(provision_actual, 2),
            variacion_provisiones=round(provision_actual - provision_anterior, 2),
            dia_ultimo_pago=fecha_ultimo_pago,
            total_recuperado=round(total_recuperado, 2),
            pendiente_pago=round(_a_float(fin.get("ValorParaEstarAlDia")), 2),
            pendiente_pago_mas_cuota_por_vencer=round(
                _a_float(fin.get("ValorHastaCuotaActual")), 2
            ),
            informacion_deudor=informacion_deudor,
            garante_1=garante_1,
            garante_2=garante_2,
        )


def _cierre_mes_anterior(fecha: date) -> date:
    return fecha.replace(day=1) - timedelta(days=1)


def _texto(valor: Any, default: str = "") -> str:
    texto = str(valor or "").strip()
    return texto or default


def _a_float(valor: Any) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _a_int(valor: Any) -> int:
    try:
        return int(valor or 0)
    except (TypeError, ValueError):
        return 0


def _a_int_opcional(valor: Any) -> int | None:
    try:
        return int(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def _es_cancelado(documento: dict[str, Any]) -> bool:
    codigo = _texto(
        documento.get("CodigoEstadoPrestamo") or documento.get("CodigoEstado")
    ).upper()
    estado = _texto(documento.get("EstadoPrestamo")).upper()
    return codigo == "C" or estado in {"C", "CANCELADO"}


def _construir_garante(
    documento: dict[str, Any],
    prefijo: str,
    fallback: dict[str, str] | None,
) -> GaranteRecaudacion | None:
    fallback = fallback or {}
    identificacion = _texto(
        documento.get(f"{prefijo}Identificacion"), fallback.get("identificacion", "")
    )
    nombres = _texto(
        documento.get(f"{prefijo}Nombres"), fallback.get("nombres", "")
    )
    if not identificacion and not nombres:
        return None
    return GaranteRecaudacion(
        identificacion=identificacion,
        nombres=nombres,
        provincia=_texto(
            documento.get(f"{prefijo}Provincia"), fallback.get("provincia", "")
        ),
        canton=_texto(
            documento.get(f"{prefijo}Canton"), fallback.get("canton", "")
        ),
        parroquia=_texto(
            documento.get(f"{prefijo}Parroquia"), fallback.get("parroquia", "")
        ),
        direccion=_texto(
            documento.get(f"{prefijo}Direccion"), fallback.get("direccion", "")
        ),
        telefonos=_texto(
            documento.get(f"{prefijo}Telefonos"), fallback.get("telefonos", "")
        ),
    )


def _calcular_provision_simulada(
    *,
    detalle: DetalleCuotaPrestamo,
    provision_actual: float,
    saldo_actual: float,
) -> float:
    saldo_simulado = max(detalle.saldo_capital_con_cobro_una_cuota, 0.0)
    if saldo_simulado == 0:
        return 0.0

    if detalle.es_porcentaje_fijo is True:
        porcentaje = detalle.porcentaje_fijo or 0.0
    elif detalle.es_porcentaje_fijo is not None:
        porcentaje = (provision_actual / saldo_actual * 100) if saldo_actual > 0 else 0.0
        if detalle.porcentaje_minimo is not None:
            porcentaje = max(porcentaje, detalle.porcentaje_minimo)
        if detalle.porcentaje_maximo not in (None, 0):
            porcentaje = min(porcentaje, detalle.porcentaje_maximo)
    else:
        porcentaje = (provision_actual / saldo_actual * 100) if saldo_actual > 0 else 0.0
    return round(saldo_simulado * porcentaje / 100, 2)

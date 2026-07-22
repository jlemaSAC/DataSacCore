import calendar
import logging
from datetime import date, datetime

from fastapi import HTTPException

from app.modules.analytic.cartera_de_credito.morosidad_historica.domain import (
    MorosidadAgrupada,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.repositories.mongo_morosidad_historica_repository import (
    MongoMorosidadHistoricaRepository,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.schemas import (
    InputMorosidadHistorica,
    MorosidadHistoricaAgrupacion,
    MorosidadHistoricaResponse,
    ResumenMensualMorosidad,
)
from app.modules.auth.schemas import AuthContext


logger = logging.getLogger("uvicorn.error")
MAX_MESES_RANGO = 60


def _valores(
    *,
    operaciones: int,
    saldo_capital: float,
    capital_vigente: float,
    capital_no_devenga: float,
    capital_vencido: float,
) -> dict[str, int | float]:
    cartera_improductiva = capital_no_devenga + capital_vencido
    morosidad = cartera_improductiva / saldo_capital if saldo_capital else 0.0
    return {
        "operaciones": operaciones,
        "saldo_capital": round(saldo_capital, 2),
        "capital_vigente": round(capital_vigente, 2),
        "capital_no_devenga": round(capital_no_devenga, 2),
        "capital_vencido": round(capital_vencido, 2),
        "cartera_improductiva": round(cartera_improductiva, 2),
        "morosidad": round(morosidad, 6),
        "morosidad_porcentaje": round(morosidad * 100, 4),
    }


class MorosidadHistoricaService:
    def __init__(self, repository: MongoMorosidadHistoricaRepository) -> None:
        self.repository = repository

    def obtener_morosidad_historica(
        self,
        input_data: InputMorosidadHistorica,
        auth_context: AuthContext,
    ) -> MorosidadHistoricaResponse:
        try:
            cortes = self._construir_cortes(input_data, auth_context)
            agrupaciones = self.repository.obtener_morosidad_agrupada(cortes)
            return self._construir_respuesta(input_data, cortes, agrupaciones)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "Error consultando morosidad historica entre %s y %s",
                input_data.periodo_desde,
                input_data.periodo_hasta,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error consultando morosidad historica: {exc}",
            ) from exc

    @staticmethod
    def _construir_cortes(
        input_data: InputMorosidadHistorica,
        auth_context: AuthContext,
    ) -> dict[str, tuple[int, int]]:
        anio_desde, mes_desde = map(int, input_data.periodo_desde.split("-"))
        anio_hasta, mes_hasta = map(int, input_data.periodo_hasta.split("-"))
        cantidad_meses = (anio_hasta - anio_desde) * 12 + mes_hasta - mes_desde + 1
        if cantidad_meses > MAX_MESES_RANGO:
            raise HTTPException(
                status_code=400,
                detail=f"El rango no puede superar {MAX_MESES_RANGO} meses.",
            )

        fecha_sistema = auth_context.usuario.fecha_sistema
        hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        ultimo_dia_hasta = date(
            anio_hasta,
            mes_hasta,
            calendar.monthrange(anio_hasta, mes_hasta)[1],
        )
        if ultimo_dia_hasta > hoy:
            raise HTTPException(
                status_code=400,
                detail="periodo_hasta debe corresponder a un mes finalizado.",
            )

        cortes: dict[str, tuple[int, int]] = {}
        anio, mes = anio_desde, mes_desde
        while (anio, mes) <= (anio_hasta, mes_hasta):
            ultimo_dia = calendar.monthrange(anio, mes)[1]
            cortes[f"{anio:04d}{mes:02d}{ultimo_dia:02d}"] = (anio, mes)
            if mes == 12:
                anio, mes = anio + 1, 1
            else:
                mes += 1
        return cortes

    @staticmethod
    def _construir_respuesta(
        input_data: InputMorosidadHistorica,
        cortes: dict[str, tuple[int, int]],
        agrupaciones: list[MorosidadAgrupada],
    ) -> MorosidadHistoricaResponse:
        acumulados = {
            f"{anio:04d}-{mes:02d}": {
                "operaciones": 0,
                "saldo_capital": 0.0,
                "capital_vigente": 0.0,
                "capital_no_devenga": 0.0,
                "capital_vencido": 0.0,
            }
            for anio, mes in cortes.values()
        }
        datos: list[MorosidadHistoricaAgrupacion] = []
        for agrupacion in sorted(agrupaciones, key=lambda item: item.dimensiones):
            dimensiones = agrupacion.dimensiones
            acumulado = acumulados[dimensiones.periodo]
            acumulado["operaciones"] += agrupacion.operaciones
            acumulado["saldo_capital"] += agrupacion.saldo_capital
            acumulado["capital_vigente"] += agrupacion.capital_vigente
            acumulado["capital_no_devenga"] += agrupacion.capital_no_devenga
            acumulado["capital_vencido"] += agrupacion.capital_vencido
            datos.append(
                MorosidadHistoricaAgrupacion(
                    **dimensiones.__dict__,
                    **_valores(
                        operaciones=agrupacion.operaciones,
                        saldo_capital=agrupacion.saldo_capital,
                        capital_vigente=agrupacion.capital_vigente,
                        capital_no_devenga=agrupacion.capital_no_devenga,
                        capital_vencido=agrupacion.capital_vencido,
                    ),
                )
            )

        corte_por_periodo = {
            f"{anio:04d}-{mes:02d}": fecha_corte
            for fecha_corte, (anio, mes) in cortes.items()
        }
        resumen = []
        for periodo, acumulado in acumulados.items():
            anio, mes = map(int, periodo.split("-"))
            resumen.append(
                ResumenMensualMorosidad(
                    periodo=periodo,
                    anio=anio,
                    mes=mes,
                    fecha_corte=corte_por_periodo[periodo],
                    **_valores(**acumulado),
                )
            )

        total = {
            campo: sum(float(item[campo]) for item in acumulados.values())
            for campo in (
                "operaciones",
                "saldo_capital",
                "capital_vigente",
                "capital_no_devenga",
                "capital_vencido",
            )
        }
        return MorosidadHistoricaResponse(
            periodo_desde=input_data.periodo_desde,
            periodo_hasta=input_data.periodo_hasta,
            **_valores(
                operaciones=int(total["operaciones"]),
                saldo_capital=total["saldo_capital"],
                capital_vigente=total["capital_vigente"],
                capital_no_devenga=total["capital_no_devenga"],
                capital_vencido=total["capital_vencido"],
            ),
            resumen_mensual=resumen,
            agrupaciones=datos,
            periodos_sin_datos=[
                periodo for periodo, valores in acumulados.items() if not valores["operaciones"]
            ],
        )


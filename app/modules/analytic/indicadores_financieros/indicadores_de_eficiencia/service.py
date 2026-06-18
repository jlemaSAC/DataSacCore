from datetime import datetime
from typing import Iterable

from fastapi import HTTPException

from app.modules.analytic.indicadores_financieros.indicadores_de_eficiencia.schemas import (
    IndicadoresDeEficienciaResponse,
    InputIndicadoresDeEficiencia,
)
from app.modules.auth.schemas import AuthContext
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import (
    SqlSaldoContableRepository,
)


CUENTAS_CORTE = (
    "45",
    "4501",
    "51",
    "41",
    "52",
    "54",
    "42",
    "53",
    "43",
    "44",
)
CUENTAS_PROMEDIO = ("1", "3")


class IndicadoresDeEficienciaService:
    def __init__(
        self,
        saldo_contable_repository: SqlSaldoContableRepository,
    ) -> None:
        self.saldo_contable_repository = saldo_contable_repository

    def calcular_indicadores_de_eficiencia(
        self,
        input_data: InputIndicadoresDeEficiencia,
        auth_context: AuthContext,
    ) -> IndicadoresDeEficienciaResponse:
        _ = auth_context
        try:
            fecha_promedio_desde = datetime(
                year=input_data.fecha_corte.year,
                month=1,
                day=1,
                tzinfo=input_data.fecha_corte.tzinfo,
            )
            saldos = self.obtener_saldos_corte(input_data)
            saldos_promedio = self.obtener_saldos_promedio(
                input_data=input_data,
                fecha_promedio_desde=fecha_promedio_desde,
            )
            mes = input_data.fecha_corte.month
            indicadores, componentes = calcular_indicadores(
                saldos=saldos,
                saldos_promedio=saldos_promedio,
                mes=mes,
            )

            return IndicadoresDeEficienciaResponse(
                fecha_corte=input_data.fecha_corte,
                fecha_promedio_desde=fecha_promedio_desde,
                id_agencia=input_data.id_agencia,
                neteo=1,
                mes=mes,
                indicadores={nombre: round_ratio(valor) for nombre, valor in indicadores.items()},
                saldos_cuentas={codigo: round_money(valor) for codigo, valor in sorted(saldos.items())},
                saldos_promedio={
                    codigo: round_money(valor) for codigo, valor in sorted(saldos_promedio.items())
                },
                componentes={codigo: round_money(valor) for codigo, valor in sorted(componentes.items())},
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando indicadores de eficiencia: {exc}",
            ) from exc

    def obtener_saldos_corte(
        self,
        input_data: InputIndicadoresDeEficiencia,
    ) -> dict[str, float]:
        codigos = codigos_unicos((CUENTAS_CORTE,))
        saldos_raw = self.saldo_contable_repository.get_saldos_contables_con_neteo(
            fecha=input_data.fecha_corte,
            id_agencia=input_data.id_agencia,
            codigos_cuenta=codigos,
            neteo=1,
        )
        saldos = {
            str(item.get("CodigoCuenta") or "").strip(): float(item.get("SaldoFinal") or 0.0)
            for item in saldos_raw
        }
        for codigo in codigos:
            saldos.setdefault(codigo, 0.0)
        return saldos

    def obtener_saldos_promedio(
        self,
        *,
        input_data: InputIndicadoresDeEficiencia,
        fecha_promedio_desde: datetime,
    ) -> dict[str, float]:
        codigos = codigos_unicos((CUENTAS_PROMEDIO,))
        saldos_raw = self.saldo_contable_repository.get_promedios_saldos_contables_con_neteo(
            fecha_desde=fecha_promedio_desde,
            fecha_hasta=input_data.fecha_corte,
            id_agencia=input_data.id_agencia,
            codigos_cuenta=codigos,
            neteo=1,
        )
        saldos = {
            str(item.get("CodigoCuenta") or "").strip(): float(item.get("SaldoPromedio") or 0.0)
            for item in saldos_raw
        }
        for codigo in codigos:
            saldos.setdefault(codigo, 0.0)
        return saldos


def calcular_indicadores(
    *,
    saldos: dict[str, float],
    saldos_promedio: dict[str, float],
    mes: int,
) -> tuple[dict[str, float | None], dict[str, float]]:
    gasto_operativo = saldos.get("45", 0.0)
    gasto_personal = saldos.get("4501", 0.0)
    gasto_operativo_estimado = anualizar(gasto_operativo, mes=mes)
    gasto_personal_estimado = anualizar(gasto_personal, mes=mes)

    activo_promedio = saldos_promedio.get("1", 0.0)
    patrimonio_promedio = saldos_promedio.get("3", 0.0)

    intereses_ganados_estimado = anualizar(saldos.get("51", 0.0), mes=mes)
    intereses_causados_estimado = anualizar(saldos.get("41", 0.0), mes=mes)
    margen_neto_intereses_estimado = intereses_ganados_estimado - intereses_causados_estimado
    comisiones_ganadas_estimado = anualizar(saldos.get("52", 0.0), mes=mes)
    ingresos_servicios_estimado = anualizar(saldos.get("54", 0.0), mes=mes)
    comisiones_causadas_estimado = anualizar(saldos.get("42", 0.0), mes=mes)
    utilidades_financieras_estimado = anualizar(saldos.get("53", 0.0), mes=mes)
    perdidas_financieras_estimado = anualizar(saldos.get("43", 0.0), mes=mes)
    margen_bruto_financiero_estimado = (
        margen_neto_intereses_estimado
        + comisiones_ganadas_estimado
        + ingresos_servicios_estimado
        - comisiones_causadas_estimado
        + utilidades_financieras_estimado
        - perdidas_financieras_estimado
    )
    provisiones_estimado = anualizar(saldos.get("44", 0.0), mes=mes)
    margen_financiero_neto_estimado = margen_bruto_financiero_estimado - provisiones_estimado
    margen_intermediacion_estimado = margen_financiero_neto_estimado - gasto_operativo_estimado

    indicadores = {
        "gasto_operativo_estimado_sobre_activo_promedio": dividir(
            gasto_operativo_estimado,
            activo_promedio,
        ),
        "gasto_personal_estimado_sobre_activo_promedio": dividir(
            gasto_personal_estimado,
            activo_promedio,
        ),
        "margen_intermediacion_estimado_sobre_patrimonio_promedio": dividir(
            margen_intermediacion_estimado,
            patrimonio_promedio,
        ),
        "margen_intermediacion_estimado_sobre_activo_promedio": dividir(
            margen_intermediacion_estimado,
            activo_promedio,
        ),
    }
    componentes = {
        "gasto_operativo": gasto_operativo,
        "gasto_operativo_estimado": gasto_operativo_estimado,
        "gasto_personal": gasto_personal,
        "gasto_personal_estimado": gasto_personal_estimado,
        "activo_promedio": activo_promedio,
        "patrimonio_promedio": patrimonio_promedio,
        "intereses_ganados_estimado": intereses_ganados_estimado,
        "intereses_causados_estimado": intereses_causados_estimado,
        "margen_neto_intereses_estimado": margen_neto_intereses_estimado,
        "comisiones_ganadas_estimado": comisiones_ganadas_estimado,
        "ingresos_servicios_estimado": ingresos_servicios_estimado,
        "comisiones_causadas_estimado": comisiones_causadas_estimado,
        "utilidades_financieras_estimado": utilidades_financieras_estimado,
        "perdidas_financieras_estimado": perdidas_financieras_estimado,
        "margen_bruto_financiero_estimado": margen_bruto_financiero_estimado,
        "provisiones_estimado": provisiones_estimado,
        "margen_financiero_neto_estimado": margen_financiero_neto_estimado,
        "margen_intermediacion_estimado": margen_intermediacion_estimado,
    }
    return indicadores, componentes


def codigos_unicos(grupos: Iterable[Iterable[str]]) -> list[str]:
    codigos: list[str] = []
    vistos: set[str] = set()
    for grupo in grupos:
        for codigo in grupo:
            codigo_normalizado = str(codigo).strip()
            if not codigo_normalizado or codigo_normalizado in vistos:
                continue
            codigos.append(codigo_normalizado)
            vistos.add(codigo_normalizado)
    return codigos


def dividir(
    numerador: float | None,
    denominador: float,
    *,
    fallback: float | None = None,
) -> float | None:
    if numerador is None or denominador == 0:
        return fallback
    return numerador / denominador


def anualizar(valor: float | None, *, mes: int) -> float:
    if valor is None or mes == 0:
        return 0.0
    return valor * 12 / mes


def round_money(valor: float) -> float:
    return round(float(valor or 0.0), 2)


def round_ratio(valor: float | None) -> float | None:
    return round(valor, 6) if valor is not None else None

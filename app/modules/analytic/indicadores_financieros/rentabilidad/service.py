from datetime import datetime
from typing import Iterable

from fastapi import HTTPException

from app.modules.analytic.indicadores_financieros.rentabilidad.schemas import (
    InputRentabilidad,
    RentabilidadResponse,
)
from app.modules.auth.schemas import AuthContext
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import (
    SqlSaldoContableRepository,
)


CUENTAS_CORTE = (
    "51",
    "41",
    "52",
    "54",
    "42",
    "53",
    "43",
    "44",
    "45",
    "5",
    "4",
    "14",
    "1499",
)
CUENTAS_PROMEDIO = ("1", "3", "21", "26")


class IndicadoresRentabilidadService:
    def __init__(
        self,
        saldo_contable_repository: SqlSaldoContableRepository,
    ) -> None:
        self.saldo_contable_repository = saldo_contable_repository

    def calcular_rentabilidad(
        self,
        input_data: InputRentabilidad,
        auth_context: AuthContext,
    ) -> RentabilidadResponse:
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

            return RentabilidadResponse(
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
                detail=f"Error calculando rentabilidad: {exc}",
            ) from exc

    def obtener_saldos_corte(self, input_data: InputRentabilidad) -> dict[str, float]:
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
        input_data: InputRentabilidad,
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
    intereses_ganados = saldos.get("51", 0.0)
    intereses_causados = saldos.get("41", 0.0)
    margen_neto_intereses = intereses_ganados - intereses_causados
    comisiones_ganadas = saldos.get("52", 0.0)
    ingresos_servicios = saldos.get("54", 0.0)
    comisiones_causadas = saldos.get("42", 0.0)
    utilidades_financieras = saldos.get("53", 0.0)
    perdidas_financieras = saldos.get("43", 0.0)
    margen_bruto_financiero = (
        margen_neto_intereses
        + comisiones_ganadas
        + ingresos_servicios
        - comisiones_causadas
        + utilidades_financieras
        - perdidas_financieras
    )
    provisiones = saldos.get("44", 0.0)
    margen_financiero_neto = margen_bruto_financiero - provisiones
    gasto_operativo = saldos.get("45", 0.0)
    gasto_operacional_sobre_margen_financiero_neto = dividir(
        gasto_operativo,
        margen_financiero_neto,
        fallback=0.0,
    )

    utilidad = saldos.get("5", 0.0) - saldos.get("4", 0.0)
    activo_promedio = saldos_promedio.get("1", 0.0)
    patrimonio_promedio = saldos_promedio.get("3", 0.0)
    roa = anualizar(dividir(utilidad, activo_promedio), mes=mes)
    roe = anualizar(dividir(utilidad, patrimonio_promedio), mes=mes)

    gasto_operativo_estimado = anualizar(gasto_operativo, mes=mes)
    cartera_bruta = saldos.get("14", 0.0) - saldos.get("1499", 0.0)
    gasto_operativo_estimado_sobre_cartera_bruta = dividir(
        gasto_operativo_estimado,
        cartera_bruta,
    )

    obligaciones_financieras_promedio = saldos_promedio.get("26", 0.0)
    obligaciones_publico_promedio = saldos_promedio.get("21", 0.0)
    costo_promedio_fondeo = anualizar(
        dividir(
            intereses_causados,
            obligaciones_financieras_promedio + obligaciones_publico_promedio,
        ),
        mes=mes,
    )

    indicadores = {
        "gasto_operacional_sobre_margen_financiero_neto": (
            gasto_operacional_sobre_margen_financiero_neto
        ),
        "roa": roa,
        "roe": roe,
        "gasto_operativo_estimado_sobre_cartera_bruta": (
            gasto_operativo_estimado_sobre_cartera_bruta
        ),
        "costo_promedio_fondeo": costo_promedio_fondeo,
    }
    componentes = {
        "intereses_ganados": intereses_ganados,
        "intereses_causados": intereses_causados,
        "margen_neto_intereses": margen_neto_intereses,
        "comisiones_ganadas": comisiones_ganadas,
        "ingresos_servicios": ingresos_servicios,
        "comisiones_causadas": comisiones_causadas,
        "utilidades_financieras": utilidades_financieras,
        "perdidas_financieras": perdidas_financieras,
        "margen_bruto_financiero": margen_bruto_financiero,
        "provisiones": provisiones,
        "margen_financiero_neto": margen_financiero_neto,
        "gasto_operativo": gasto_operativo,
        "utilidad": utilidad,
        "activo_promedio": activo_promedio,
        "patrimonio_promedio": patrimonio_promedio,
        "gasto_operativo_estimado": gasto_operativo_estimado,
        "cartera_bruta": cartera_bruta,
        "obligaciones_financieras_promedio": obligaciones_financieras_promedio,
        "obligaciones_publico_promedio": obligaciones_publico_promedio,
        "obligaciones_fondeo_promedio": (
            obligaciones_financieras_promedio + obligaciones_publico_promedio
        ),
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


def anualizar(valor: float | None, *, mes: int) -> float | None:
    if valor is None or mes == 0:
        return None
    return valor * 12 / mes


def round_money(valor: float) -> float:
    return round(float(valor or 0.0), 2)


def round_ratio(valor: float | None) -> float | None:
    return round(valor, 6) if valor is not None else None

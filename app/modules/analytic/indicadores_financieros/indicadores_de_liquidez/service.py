from typing import Iterable

from fastapi import HTTPException

from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.schemas import (
    IndicadoresDeLiquidezResponse,
    InputIndicadoresDeLiquidez,
)
from app.modules.auth.schemas import AuthContext
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import (
    SqlSaldoContableRepository,
)


CUENTAS_FONDOS_DISPONIBLES_DEPOSITOS_CORTO_PLAZO = ("11", "2101", "210305", "210310")
CUENTAS_LIQUIDEZ_OBLIGACIONES_PUBLICO = ("11", "21")
CUENTAS_LIQUIDEZ_INVERSIONES_DEPOSITOS = ("11", "13", "2101", "2103")

ACTIVO_LIQUIDO_PASIVO_EXIGIBLE = (
    "11",
    "1201",
    "130105",
    "130150",
    "130205",
    "130305",
    "130310",
    "130350",
    "130355",
    "1304",
    "130605",
    "130610",
    "130615",
)
PASIVO_EXIGIBLE = ("2101", "2201", "23", "2102", "2103", "2105", "24", "26", "27", "2903")

CUENTAS_INVERSIONES_OBLIGACIONES_PUBLICO = ("13", "21")
ACTIVO_LIQUIDO_OBLIGACIONES_PUBLICO = ("11", "1105", "1201", "1202", "130115", "130365", "1306")
OBLIGACIONES_PUBLICO_ACTIVO_LIQUIDO = ("2101", "2103", "2104", "2105", "2903", "2104")

NUMERADOR_PRIMERA_LINEA = (
    ("11", 1.0),
    ("1105", -1.0),
    ("1201", 1.0),
    ("2201", -1.0),
    ("1202", 1.0),
    ("2102", -1.0),
    ("2202", -1.0),
    ("130105", 1.0),
    ("130110", 1.0),
    ("130150", 1.0),
    ("130155", 1.0),
    ("130205", 1.0),
    ("130210", 1.0),
    ("130305", 1.0),
    ("130310", 1.0),
    ("130350", 1.0),
    ("130355", 1.0),
    ("130405", 1.0),
    ("130410", 1.0),
    ("190286", 1.0),
)
DENOMINADOR_PRIMERA_LINEA = (
    "2101",
    "210305",
    "210310",
    "23",
    "24",
    "2601",
    "260205",
    "260210",
    "260250",
    "260255",
    "260305",
    "260310",
    "260450",
    "260455",
    "260605",
    "260610",
    "260705",
    "260710",
    "261005",
    "261010",
    "261015",
    "261090",
    "27",
    "2903",
)

NUMERADOR_SEGUNDA_LINEA = (
    ("11", 1.0),
    ("1105", -1.0),
    ("1201", 1.0),
    ("2201", -1.0),
    ("1202", 1.0),
    ("2102", -1.0),
    ("2202", -1.0),
    ("130105", 1.0),
    ("130110", 1.0),
    ("130115", 1.0),
    ("130150", 1.0),
    ("130155", 1.0),
    ("130160", 1.0),
    ("130205", 1.0),
    ("130210", 1.0),
    ("130215", 1.0),
    ("130305", 1.0),
    ("130310", 1.0),
    ("130315", 1.0),
    ("130350", 1.0),
    ("130355", 1.0),
    ("130360", 1.0),
    ("130405", 1.0),
    ("130410", 1.0),
    ("130415", 1.0),
    ("130505", 1.0),
    ("130510", 1.0),
    ("130515", 1.0),
    ("130550", 1.0),
    ("130555", 1.0),
    ("130560", 1.0),
    ("130605", 1.0),
    ("130610", 1.0),
    ("130615", 1.0),
    ("190286", 1.0),
)
DENOMINADOR_SEGUNDA_LINEA = (
    "2101",
    "2103",
    "2105",
    "23",
    "2601",
    "260205",
    "260210",
    "260215",
    "260220",
    "260250",
    "260255",
    "260260",
    "260310",
    "260315",
    "260320",
    "260450",
    "260455",
    "260460",
    "260465",
    "260605",
    "260610",
    "260615",
    "260620",
    "260705",
    "260710",
    "260715",
    "260720",
    "261005",
    "261010",
    "261090",
    "27",
    "2903",
)


class IndicadoresDeLiquidezService:
    def __init__(
        self,
        saldo_contable_repository: SqlSaldoContableRepository,
    ) -> None:
        self.saldo_contable_repository = saldo_contable_repository

    def calcular_indicadores_de_liquidez(
        self,
        input_data: InputIndicadoresDeLiquidez,
        auth_context: AuthContext,
    ) -> IndicadoresDeLiquidezResponse:
        _ = auth_context
        try:
            codigos = codigos_unicos(
                (
                    CUENTAS_FONDOS_DISPONIBLES_DEPOSITOS_CORTO_PLAZO,
                    CUENTAS_LIQUIDEZ_OBLIGACIONES_PUBLICO,
                    CUENTAS_LIQUIDEZ_INVERSIONES_DEPOSITOS,
                    ACTIVO_LIQUIDO_PASIVO_EXIGIBLE,
                    PASIVO_EXIGIBLE,
                    CUENTAS_INVERSIONES_OBLIGACIONES_PUBLICO,
                    ACTIVO_LIQUIDO_OBLIGACIONES_PUBLICO,
                    OBLIGACIONES_PUBLICO_ACTIVO_LIQUIDO,
                    codigos_componentes(NUMERADOR_PRIMERA_LINEA),
                    DENOMINADOR_PRIMERA_LINEA,
                    codigos_componentes(NUMERADOR_SEGUNDA_LINEA),
                    DENOMINADOR_SEGUNDA_LINEA,
                )
            )
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

            indicadores, componentes = calcular_indicadores(saldos)

            return IndicadoresDeLiquidezResponse(
                fecha_corte=input_data.fecha_corte,
                id_agencia=input_data.id_agencia,
                neteo=1,
                indicadores={nombre: round_ratio(valor) for nombre, valor in indicadores.items()},
                saldos_cuentas={codigo: round_money(valor) for codigo, valor in sorted(saldos.items())},
                componentes={codigo: round_money(valor) for codigo, valor in sorted(componentes.items())},
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando indicadores de liquidez: {exc}",
            ) from exc


def calcular_indicadores(
    saldos: dict[str, float],
) -> tuple[dict[str, float | None], dict[str, float]]:
    fondos_disponibles = saldos.get("11", 0.0)
    depositos_corto_plazo = sumar(saldos, ("2101", "210305", "210310"))
    liquidez_depositos_corto_plazo = dividir(
        fondos_disponibles,
        depositos_corto_plazo,
        fallback=0.0,
    )

    obligaciones_publico = saldos.get("21", 0.0)
    liquidez_obligaciones_publico = dividir(fondos_disponibles, obligaciones_publico)

    inversiones = saldos.get("13", 0.0)
    depositos_vista_plazo = sumar(saldos, ("2101", "2103"))
    liquidez_inversiones_depositos = dividir(
        fondos_disponibles + inversiones,
        depositos_vista_plazo,
    )

    activo_liquido_pasivo_exigible = sumar(saldos, ACTIVO_LIQUIDO_PASIVO_EXIGIBLE)
    pasivo_exigible = sumar(saldos, PASIVO_EXIGIBLE)
    activos_liquidos_sobre_pasivos_exigibles = dividir(
        activo_liquido_pasivo_exigible,
        pasivo_exigible,
    )

    inversiones_sobre_obligaciones_publico = dividir(inversiones, obligaciones_publico)

    activo_liquido_obligaciones_publico = sumar(saldos, ACTIVO_LIQUIDO_OBLIGACIONES_PUBLICO)
    obligaciones_publico_activo_liquido = sumar(saldos, OBLIGACIONES_PUBLICO_ACTIVO_LIQUIDO)
    activos_liquidos_sobre_obligaciones_publico = dividir(
        activo_liquido_obligaciones_publico,
        obligaciones_publico_activo_liquido,
    )

    liquidez_primera_linea_numerador = sumar_componentes(saldos, NUMERADOR_PRIMERA_LINEA)
    liquidez_primera_linea_denominador = sumar(saldos, DENOMINADOR_PRIMERA_LINEA)
    liquidez_primera_linea = dividir(
        liquidez_primera_linea_numerador,
        liquidez_primera_linea_denominador,
    )

    liquidez_segunda_linea_numerador = sumar_componentes(saldos, NUMERADOR_SEGUNDA_LINEA)
    liquidez_segunda_linea_denominador = sumar(saldos, DENOMINADOR_SEGUNDA_LINEA)
    liquidez_segunda_linea = dividir(
        liquidez_segunda_linea_numerador,
        liquidez_segunda_linea_denominador,
    )

    indicadores = {
        "fondos_disponibles_sobre_depositos_corto_plazo": liquidez_depositos_corto_plazo,
        "liquidez_sobre_obligaciones_publico": liquidez_obligaciones_publico,
        "liquidez_inversiones_sobre_depositos_vista_plazo": liquidez_inversiones_depositos,
        "activos_liquidos_sobre_pasivos_exigibles": activos_liquidos_sobre_pasivos_exigibles,
        "inversiones_sobre_obligaciones_publico": inversiones_sobre_obligaciones_publico,
        "activos_liquidos_sobre_obligaciones_publico": activos_liquidos_sobre_obligaciones_publico,
        "liquidez_primera_linea": liquidez_primera_linea,
        "liquidez_segunda_linea": liquidez_segunda_linea,
    }
    componentes = {
        "fondos_disponibles": fondos_disponibles,
        "depositos_corto_plazo": depositos_corto_plazo,
        "obligaciones_publico": obligaciones_publico,
        "inversiones": inversiones,
        "depositos_vista_plazo": depositos_vista_plazo,
        "activo_liquido_pasivo_exigible": activo_liquido_pasivo_exigible,
        "pasivo_exigible": pasivo_exigible,
        "activo_liquido_obligaciones_publico": activo_liquido_obligaciones_publico,
        "obligaciones_publico_activo_liquido": obligaciones_publico_activo_liquido,
        "liquidez_primera_linea_numerador": liquidez_primera_linea_numerador,
        "liquidez_primera_linea_denominador": liquidez_primera_linea_denominador,
        "liquidez_segunda_linea_numerador": liquidez_segunda_linea_numerador,
        "liquidez_segunda_linea_denominador": liquidez_segunda_linea_denominador,
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


def codigos_componentes(componentes: Iterable[tuple[str, float]]) -> list[str]:
    return [codigo for codigo, _factor in componentes]


def sumar(saldos: dict[str, float], codigos: Iterable[str]) -> float:
    return sum(float(saldos.get(codigo, 0.0)) for codigo in codigos)


def sumar_componentes(
    saldos: dict[str, float],
    componentes: Iterable[tuple[str, float]],
) -> float:
    return sum(float(saldos.get(codigo, 0.0)) * factor for codigo, factor in componentes)


def dividir(
    numerador: float,
    denominador: float,
    *,
    fallback: float | None = None,
) -> float | None:
    if denominador == 0:
        return fallback
    return numerador / denominador


def round_money(valor: float) -> float:
    return round(float(valor or 0.0), 2)


def round_ratio(valor: float | None) -> float | None:
    return round(valor, 6) if valor is not None else None

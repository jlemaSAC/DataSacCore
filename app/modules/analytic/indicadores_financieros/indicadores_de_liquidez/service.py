from calendar import monthrange
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.schemas import (
    IndicadorDeLiquidezMensual,
    IndicadoresDeLiquidezHistoricoResponse,
    IndicadoresDeLiquidezResponse,
    InputIndicadoresDeLiquidez,
    InputIndicadoresDeLiquidezHistorico,
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

TIMEZONE_ECUADOR = ZoneInfo("America/Guayaquil")
INDICADORES_TABLA = (
    "fondos_disponibles_sobre_depositos_corto_plazo",
    "liquidez_sobre_obligaciones_publico",
    "liquidez_inversiones_sobre_depositos_vista_plazo",
    "activos_liquidos_sobre_pasivos_exigibles",
    "inversiones_sobre_obligaciones_publico",
    "activos_liquidos_sobre_obligaciones_publico",
    "liquidez_primera_linea",
    "liquidez_segunda_linea",
)
MAX_FECHAS_POR_CONSULTA = 1000


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
            codigos = obtener_codigos_cuentas_liquidez()
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

    def consultar_indicadores_de_liquidez_historico(
        self,
        input_data: InputIndicadoresDeLiquidezHistorico,
        auth_context: AuthContext,
    ) -> IndicadoresDeLiquidezHistoricoResponse:
        _ = auth_context
        try:
            hoy = fecha_actual_ecuador()
            fechas_consulta = construir_fechas_consulta(
                periodo_desde=input_data.periodo_desde,
                periodo_hasta=input_data.periodo_hasta,
                hoy=hoy,
            )
            return self._consultar_indicadores_por_fechas(
                input_data=input_data,
                fechas_consulta=fechas_consulta,
                formato_sin_datos="%Y-%m",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando indicadores de liquidez: {exc}",
            ) from exc

    def consultar_indicadores_de_liquidez_historico_diario(
        self,
        input_data: InputIndicadoresDeLiquidezHistorico,
        auth_context: AuthContext,
    ) -> IndicadoresDeLiquidezHistoricoResponse:
        _ = auth_context
        try:
            fechas_consulta = construir_fechas_consulta_diaria(
                periodo_desde=input_data.periodo_desde,
                periodo_hasta=input_data.periodo_hasta,
                hoy=fecha_actual_ecuador(),
            )
            return self._consultar_indicadores_por_fechas(
                input_data=input_data,
                fechas_consulta=fechas_consulta,
                formato_sin_datos="%Y-%m-%d",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando indicadores de liquidez: {exc}",
            ) from exc

    def _consultar_indicadores_por_fechas(
        self,
        *,
        input_data: InputIndicadoresDeLiquidezHistorico,
        fechas_consulta: list[date],
        formato_sin_datos: str,
    ) -> IndicadoresDeLiquidezHistoricoResponse:
        codigos = obtener_codigos_cuentas_liquidez()
        saldos_raw: list[dict[str, Any]] = []
        for posicion in range(0, len(fechas_consulta), MAX_FECHAS_POR_CONSULTA):
            lote = fechas_consulta[posicion : posicion + MAX_FECHAS_POR_CONSULTA]
            saldos_raw.extend(
                self.saldo_contable_repository.get_saldos_contables_fechas_con_neteo(
                    fechas=[datetime.combine(fecha, time.min) for fecha in lote],
                    id_agencia=input_data.id_agencia,
                    codigos_cuenta=codigos,
                    neteo=1,
                )
            )

        saldos_por_fecha = agrupar_saldos_por_fecha(saldos_raw)
        datos: list[IndicadorDeLiquidezMensual] = []
        periodos_sin_datos: list[str] = []

        for fecha_corte in fechas_consulta:
            saldos = saldos_por_fecha.get(fecha_corte)
            if not saldos:
                periodos_sin_datos.append(fecha_corte.strftime(formato_sin_datos))
                continue

            for codigo in codigos:
                saldos.setdefault(codigo, 0.0)
            indicadores, _componentes = calcular_indicadores(saldos)
            valores = {nombre: round_ratio(indicadores[nombre]) for nombre in INDICADORES_TABLA}
            datos.append(
                IndicadorDeLiquidezMensual(
                    fecha_corte=fecha_corte,
                    anio=fecha_corte.year,
                    mes=fecha_corte.month,
                    dia=fecha_corte.day,
                    **valores,
                )
            )

        return IndicadoresDeLiquidezHistoricoResponse(
            id_agencia=input_data.id_agencia,
            periodo_desde=input_data.periodo_desde,
            periodo_hasta=input_data.periodo_hasta,
            neteo=1,
            datos=datos,
            periodos_sin_datos=periodos_sin_datos,
        )


def obtener_codigos_cuentas_liquidez() -> list[str]:
    return codigos_unicos(
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


def fecha_actual_ecuador() -> date:
    return datetime.now(TIMEZONE_ECUADOR).date()


def construir_fechas_consulta(
    *,
    periodo_desde: str,
    periodo_hasta: str,
    hoy: date,
) -> list[date]:
    mes_desde, mes_hasta, mes_actual = validar_periodos_consulta(
        periodo_desde=periodo_desde,
        periodo_hasta=periodo_hasta,
        hoy=hoy,
    )

    fechas: list[date] = []
    cursor = mes_desde
    while cursor <= mes_hasta:
        if cursor == mes_actual:
            fechas.append(hoy)
        else:
            ultimo_dia = monthrange(cursor.year, cursor.month)[1]
            fechas.append(cursor.replace(day=ultimo_dia))
        cursor = siguiente_mes(cursor)
    return fechas


def construir_fechas_consulta_diaria(
    *,
    periodo_desde: str,
    periodo_hasta: str,
    hoy: date,
) -> list[date]:
    mes_desde, mes_hasta, mes_actual = validar_periodos_consulta(
        periodo_desde=periodo_desde,
        periodo_hasta=periodo_hasta,
        hoy=hoy,
    )
    if mes_hasta == mes_actual:
        fecha_hasta = hoy
    else:
        fecha_hasta = mes_hasta.replace(day=monthrange(mes_hasta.year, mes_hasta.month)[1])

    total_dias = (fecha_hasta - mes_desde).days
    return [mes_desde + timedelta(days=desplazamiento) for desplazamiento in range(total_dias + 1)]


def validar_periodos_consulta(
    *,
    periodo_desde: str,
    periodo_hasta: str,
    hoy: date,
) -> tuple[date, date, date]:
    mes_desde = date.fromisoformat(f"{periodo_desde}-01")
    mes_hasta = date.fromisoformat(f"{periodo_hasta}-01")
    mes_actual = hoy.replace(day=1)

    if mes_desde > mes_hasta:
        raise HTTPException(
            status_code=400,
            detail="periodo_desde no puede ser posterior a periodo_hasta.",
        )
    if mes_hasta > mes_actual:
        raise HTTPException(
            status_code=400,
            detail="No se pueden consultar periodos posteriores a la fecha actual.",
        )
    return mes_desde, mes_hasta, mes_actual


def siguiente_mes(fecha: date) -> date:
    if fecha.month == 12:
        return date(fecha.year + 1, 1, 1)
    return date(fecha.year, fecha.month + 1, 1)


def agrupar_saldos_por_fecha(
    saldos_raw: Iterable[dict[str, Any]],
) -> dict[date, dict[str, float]]:
    saldos_por_fecha: dict[date, dict[str, float]] = {}
    for item in saldos_raw:
        fecha = normalizar_fecha(item.get("Fecha"))
        codigo = str(item.get("CodigoCuenta") or "").strip()
        if fecha is None or not codigo:
            continue
        saldos_por_fecha.setdefault(fecha, {})[codigo] = float(item.get("SaldoFinal") or 0.0)
    return saldos_por_fecha


def normalizar_fecha(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        try:
            return datetime.fromisoformat(valor).date()
        except ValueError:
            return None
    return None


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

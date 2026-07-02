from datetime import date, datetime, time, timedelta
from typing import Any, Iterable

from fastapi import HTTPException

from app.modules.analytic.indicadores_financieros.fechas_historicas import (
    MAX_FECHAS_POR_CONSULTA,
    construir_fechas_consulta_diaria,
    construir_fechas_consulta_mensual,
    fecha_actual_ecuador,
)
from app.modules.analytic.indicadores_financieros.rentabilidad.schemas import (
    InputRentabilidad,
    InputRentabilidadHistorico,
    RentabilidadHistoricoItem,
    RentabilidadHistoricoResponse,
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
INDICADORES_RENTABILIDAD_HISTORICO = (
    "gasto_operacional_sobre_margen_financiero_neto",
    "roa",
    "roe",
    "gasto_operativo_estimado_sobre_cartera_bruta",
    "costo_promedio_fondeo",
)


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
            return self._calcular_rentabilidad_desde_saldos(
                input_data=input_data,
                fecha_promedio_desde=fecha_promedio_desde,
                saldos=saldos,
                saldos_promedio=saldos_promedio,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando rentabilidad: {exc}",
            ) from exc

    def consultar_rentabilidad_historico_mensual(
        self,
        input_data: InputRentabilidadHistorico,
        auth_context: AuthContext,
    ) -> RentabilidadHistoricoResponse:
        _ = auth_context
        try:
            fechas_consulta = construir_fechas_consulta_mensual(
                periodo_desde=input_data.periodo_desde,
                periodo_hasta=input_data.periodo_hasta,
                hoy=fecha_actual_ecuador(),
            )
            return self._consultar_rentabilidad_por_fechas(
                input_data=input_data,
                fechas_consulta=fechas_consulta,
                formato_sin_datos="%Y-%m",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando historico mensual de rentabilidad: {exc}",
            ) from exc

    def consultar_rentabilidad_historico_diario(
        self,
        input_data: InputRentabilidadHistorico,
        auth_context: AuthContext,
    ) -> RentabilidadHistoricoResponse:
        _ = auth_context
        try:
            fechas_consulta = construir_fechas_consulta_diaria(
                periodo_desde=input_data.periodo_desde,
                periodo_hasta=input_data.periodo_hasta,
                hoy=fecha_actual_ecuador(),
            )
            return self._consultar_rentabilidad_por_fechas(
                input_data=input_data,
                fechas_consulta=fechas_consulta,
                formato_sin_datos="%Y-%m-%d",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando historico diario de rentabilidad: {exc}",
            ) from exc

    def _consultar_rentabilidad_por_fechas(
        self,
        *,
        input_data: InputRentabilidadHistorico,
        fechas_consulta: list[date],
        formato_sin_datos: str,
    ) -> RentabilidadHistoricoResponse:
        saldos_corte_raw = self._obtener_saldos_fechas(
            fechas=fechas_consulta,
            id_agencia=input_data.id_agencia,
            codigos=CUENTAS_CORTE,
        )
        saldos_corte_por_fecha = agrupar_saldos_por_fecha(saldos_corte_raw)

        fechas_promedio = construir_fechas_promedio_necesarias(fechas_consulta)
        saldos_promedio_raw = self._obtener_saldos_fechas(
            fechas=fechas_promedio,
            id_agencia=input_data.id_agencia,
            codigos=CUENTAS_PROMEDIO,
        )
        saldos_promedio_por_fecha = agrupar_saldos_por_fecha(saldos_promedio_raw)

        codigos_corte = codigos_unicos((CUENTAS_CORTE,))
        datos: list[RentabilidadHistoricoItem] = []
        periodos_sin_datos: list[str] = []

        for fecha_corte in fechas_consulta:
            saldos = saldos_corte_por_fecha.get(fecha_corte)
            if not saldos:
                periodos_sin_datos.append(fecha_corte.strftime(formato_sin_datos))
                continue
            for codigo in codigos_corte:
                saldos.setdefault(codigo, 0.0)

            fecha_promedio_desde = datetime(fecha_corte.year, 1, 1)
            saldos_promedio = calcular_saldos_promedio_hasta_fecha(
                saldos_por_fecha=saldos_promedio_por_fecha,
                fecha_corte=fecha_corte,
                codigos=CUENTAS_PROMEDIO,
            )
            resultado = self._calcular_rentabilidad_desde_saldos(
                input_data=InputRentabilidad(
                    fecha_corte=datetime.combine(fecha_corte, time.min),
                    id_agencia=input_data.id_agencia,
                ),
                fecha_promedio_desde=fecha_promedio_desde,
                saldos=saldos,
                saldos_promedio=saldos_promedio,
            )
            valores = {
                nombre: resultado.indicadores.get(nombre)
                for nombre in INDICADORES_RENTABILIDAD_HISTORICO
            }
            datos.append(
                RentabilidadHistoricoItem(
                    fecha_corte=fecha_corte,
                    anio=fecha_corte.year,
                    mes=fecha_corte.month,
                    dia=fecha_corte.day,
                    **valores,
                )
            )

        return RentabilidadHistoricoResponse(
            id_agencia=input_data.id_agencia,
            periodo_desde=input_data.periodo_desde,
            periodo_hasta=input_data.periodo_hasta,
            neteo=1,
            datos=datos,
            periodos_sin_datos=periodos_sin_datos,
        )

    def _obtener_saldos_fechas(
        self,
        *,
        fechas: list[date],
        id_agencia: int,
        codigos: Iterable[str],
    ) -> list[dict[str, Any]]:
        codigos_normalizados = codigos_unicos((codigos,))
        saldos_raw: list[dict[str, Any]] = []
        for posicion in range(0, len(fechas), MAX_FECHAS_POR_CONSULTA):
            lote = fechas[posicion : posicion + MAX_FECHAS_POR_CONSULTA]
            saldos_raw.extend(
                self.saldo_contable_repository.get_saldos_contables_fechas_con_neteo(
                    fechas=[datetime.combine(fecha, time.min) for fecha in lote],
                    id_agencia=id_agencia,
                    codigos_cuenta=codigos_normalizados,
                    neteo=1,
                )
            )
        return saldos_raw

    def _calcular_rentabilidad_desde_saldos(
        self,
        *,
        input_data: InputRentabilidad,
        fecha_promedio_desde: datetime,
        saldos: dict[str, float],
        saldos_promedio: dict[str, float],
    ) -> RentabilidadResponse:
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


def construir_fechas_promedio_necesarias(fechas_corte: Iterable[date]) -> list[date]:
    ultima_fecha_por_anio: dict[int, date] = {}
    for fecha_corte in fechas_corte:
        ultima_fecha = ultima_fecha_por_anio.get(fecha_corte.year)
        if ultima_fecha is None or fecha_corte > ultima_fecha:
            ultima_fecha_por_anio[fecha_corte.year] = fecha_corte

    fechas: list[date] = []
    for anio, fecha_hasta in sorted(ultima_fecha_por_anio.items()):
        fecha_desde = date(anio, 1, 1)
        total_dias = (fecha_hasta - fecha_desde).days
        fechas.extend(
            fecha_desde + timedelta(days=desplazamiento)
            for desplazamiento in range(total_dias + 1)
        )
    return fechas


def calcular_saldos_promedio_hasta_fecha(
    *,
    saldos_por_fecha: dict[date, dict[str, float]],
    fecha_corte: date,
    codigos: Iterable[str],
) -> dict[str, float]:
    codigos_normalizados = codigos_unicos((codigos,))
    sumas = {codigo: 0.0 for codigo in codigos_normalizados}
    cantidades = {codigo: 0 for codigo in codigos_normalizados}

    for fecha, saldos in saldos_por_fecha.items():
        if fecha.year != fecha_corte.year or fecha > fecha_corte:
            continue
        for codigo in codigos_normalizados:
            if codigo not in saldos:
                continue
            sumas[codigo] += float(saldos[codigo])
            cantidades[codigo] += 1

    return {
        codigo: sumas[codigo] / cantidades[codigo] if cantidades[codigo] else 0.0
        for codigo in codigos_normalizados
    }


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

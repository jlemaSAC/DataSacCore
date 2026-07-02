from datetime import date, datetime, time
from typing import Any, Iterable

from fastapi import HTTPException

from app.modules.analytic.indicadores_financieros.calidad_de_activos.schemas import (
    CalidadDeActivosHistoricoItem,
    CalidadDeActivosHistoricoResponse,
    CalidadDeActivosResponse,
    InputCalidadDeActivos,
    InputCalidadDeActivosHistorico,
)
from app.modules.analytic.indicadores_financieros.fechas_historicas import (
    MAX_FECHAS_POR_CONSULTA,
    construir_fechas_consulta_diaria,
    construir_fechas_consulta_mensual,
    fecha_actual_ecuador,
)
from app.modules.auth.schemas import AuthContext
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import (
    SqlSaldoContableRepository,
)


CARTERA_POR_VENCER_AMPLIADA = (
    "1401",
    "1402",
    "1403",
    "1404",
    "1408",
    "1409",
    "1410",
    "1411",
    "1412",
    "1416",
    "1417",
    "1418",
    "1419",
    "1420",
    "1424",
    "1473",
    "1475",
    "1477",
)
CARTERA_NO_DEVENGA_AMPLIADA = (
    "1425",
    "1426",
    "1427",
    "1428",
    "1432",
    "1433",
    "1434",
    "1435",
    "1436",
    "1440",
    "1441",
    "1442",
    "1443",
    "1444",
    "1448",
    "1479",
    "1481",
    "1483",
)
VENCIDA_AMPLIADA = (
    "1449",
    "1450",
    "1451",
    "1452",
    "1456",
    "1457",
    "1458",
    "1459",
    "1460",
    "1464",
    "1465",
    "1466",
    "1467",
    "1468",
    "1472",
    "1485",
    "1487",
    "1489",
)

CARTERA_POR_VENCER_CONSUMO = ("1402", "1410", "1418")
CARTERA_NO_DEVENGA_CONSUMO = ("1426", "1434", "1442")
VENCIDA_CONSUMO = ("1450", "1458", "1466")

CARTERA_POR_VENCER_INMOBILIARIA = ("1403", "1411", "1419")
CARTERA_NO_DEVENGA_INMOBILIARIA = ("1427", "1435", "1443")
VENCIDA_INMOBILIARIA = ("1451", "1459", "1467")

CARTERA_POR_VENCER_MICRO = ("1404", "1412", "1420")
CARTERA_NO_DEVENGA_MICRO = ("1428", "1436", "1444")
VENCIDA_MICRO = ("1452", "1460", "1468")

CUENTAS_FONDOS = ("11", "1103")
CARTERA_NO_DEVENGA_ACTIVOS_IMPRODUCTIVOS = (
    "1425",
    "1426",
    "1427",
    "1428",
    "1429",
    "1430",
    "1433",
    "1434",
    "1435",
    "1436",
    "1437",
    "1438",
    "1441",
    "1442",
    "1443",
    "1444",
    "1445",
    "1446",
)
VENCIDA_ACTIVOS_IMPRODUCTIVOS = (
    "1449",
    "1450",
    "1451",
    "1452",
    "1453",
    "1454",
    "1455",
    "1456",
    "1457",
    "1458",
    "1459",
    "1460",
    "1461",
    "1462",
    "1465",
    "1466",
    "1467",
    "1468",
    "1469",
    "1470",
)
CUENTAS_POR_COBRAR = ("16", "1699")
CUENTAS_BIENES_ADJUDICADOS = ("17", "170105", "170110", "170115", "1799")
CUENTAS_OTROS_ACTIVOS = (
    "19",
    "1999",
    "1901",
    "190205",
    "190210",
    "190215",
    "190220",
    "190240",
    "190250",
    "190280",
    "190286",
    "1903",
)
CUENTAS_PROVISIONES_IMPRODUCTIVOS = ("1499", "1699", "1799", "1999")
CUENTAS_ACTIVO = ("1",)
CUENTAS_CARTERA_BRUTA = ("14", "1499")
CUENTAS_CARTERA_REFINANCIADA = ("1410", "1412", "1436", "1460")
CUENTAS_CARTERA_RESTRUCTURADA = ("1418", "1420", "1444", "1466", "1468")
INDICADORES_CALIDAD_DE_ACTIVOS_HISTORICO = (
    "morosidad_ampliada",
    "morosidad_consumo",
    "morosidad_inmobiliaria",
    "morosidad_micro",
    "activos_improductivos_netos_sobre_activo",
    "cartera_refinanciada_restructurada_sobre_cartera_total",
    "cartera_bruta_sobre_activos",
    "cobertura_cartera_en_riesgo",
)


class IndicadoresCalidadDeActivosService:
    def __init__(
        self,
        saldo_contable_repository: SqlSaldoContableRepository,
    ) -> None:
        self.saldo_contable_repository = saldo_contable_repository

    def calcular_calidad_de_activos(
        self,
        input_data: InputCalidadDeActivos,
        auth_context: AuthContext,
    ) -> CalidadDeActivosResponse:
        _ = auth_context
        try:
            codigos = obtener_codigos_cuentas_calidad_de_activos()
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

            return self._calcular_calidad_de_activos_desde_saldos(
                input_data=input_data,
                saldos=saldos,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando calidad de activos: {exc}",
            ) from exc

    def consultar_calidad_de_activos_historico_mensual(
        self,
        input_data: InputCalidadDeActivosHistorico,
        auth_context: AuthContext,
    ) -> CalidadDeActivosHistoricoResponse:
        _ = auth_context
        try:
            fechas_consulta = construir_fechas_consulta_mensual(
                periodo_desde=input_data.periodo_desde,
                periodo_hasta=input_data.periodo_hasta,
                hoy=fecha_actual_ecuador(),
            )
            return self._consultar_calidad_de_activos_por_fechas(
                input_data=input_data,
                fechas_consulta=fechas_consulta,
                formato_sin_datos="%Y-%m",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando historico mensual de calidad de activos: {exc}",
            ) from exc

    def consultar_calidad_de_activos_historico_diario(
        self,
        input_data: InputCalidadDeActivosHistorico,
        auth_context: AuthContext,
    ) -> CalidadDeActivosHistoricoResponse:
        _ = auth_context
        try:
            fechas_consulta = construir_fechas_consulta_diaria(
                periodo_desde=input_data.periodo_desde,
                periodo_hasta=input_data.periodo_hasta,
                hoy=fecha_actual_ecuador(),
            )
            return self._consultar_calidad_de_activos_por_fechas(
                input_data=input_data,
                fechas_consulta=fechas_consulta,
                formato_sin_datos="%Y-%m-%d",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando historico diario de calidad de activos: {exc}",
            ) from exc

    def _consultar_calidad_de_activos_por_fechas(
        self,
        *,
        input_data: InputCalidadDeActivosHistorico,
        fechas_consulta: list[date],
        formato_sin_datos: str,
    ) -> CalidadDeActivosHistoricoResponse:
        codigos = obtener_codigos_cuentas_calidad_de_activos()
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
        datos: list[CalidadDeActivosHistoricoItem] = []
        periodos_sin_datos: list[str] = []

        for fecha_corte in fechas_consulta:
            saldos = saldos_por_fecha.get(fecha_corte)
            if not saldos:
                periodos_sin_datos.append(fecha_corte.strftime(formato_sin_datos))
                continue

            for codigo in codigos:
                saldos.setdefault(codigo, 0.0)
            resultado = self._calcular_calidad_de_activos_desde_saldos(
                input_data=InputCalidadDeActivos(
                    fecha_corte=datetime.combine(fecha_corte, time.min),
                    id_agencia=input_data.id_agencia,
                ),
                saldos=saldos,
            )
            valores = {
                nombre: resultado.indicadores.get(nombre)
                for nombre in INDICADORES_CALIDAD_DE_ACTIVOS_HISTORICO
            }
            datos.append(
                CalidadDeActivosHistoricoItem(
                    fecha_corte=fecha_corte,
                    anio=fecha_corte.year,
                    mes=fecha_corte.month,
                    dia=fecha_corte.day,
                    **valores,
                )
            )

        return CalidadDeActivosHistoricoResponse(
            id_agencia=input_data.id_agencia,
            periodo_desde=input_data.periodo_desde,
            periodo_hasta=input_data.periodo_hasta,
            neteo=1,
            datos=datos,
            periodos_sin_datos=periodos_sin_datos,
        )

    def _calcular_calidad_de_activos_desde_saldos(
        self,
        *,
        input_data: InputCalidadDeActivos,
        saldos: dict[str, float],
    ) -> CalidadDeActivosResponse:
        mora_ampliada, componentes_mora_ampliada = calcular_morosidad(
            saldos,
            cartera_por_vencer=CARTERA_POR_VENCER_AMPLIADA,
            cartera_no_devenga=CARTERA_NO_DEVENGA_AMPLIADA,
            vencida=VENCIDA_AMPLIADA,
            prefijo="morosidad_ampliada",
        )
        mora_consumo, componentes_mora_consumo = calcular_morosidad(
            saldos,
            cartera_por_vencer=CARTERA_POR_VENCER_CONSUMO,
            cartera_no_devenga=CARTERA_NO_DEVENGA_CONSUMO,
            vencida=VENCIDA_CONSUMO,
            prefijo="morosidad_consumo",
        )
        mora_inmobiliaria, componentes_mora_inmobiliaria = calcular_morosidad(
            saldos,
            cartera_por_vencer=CARTERA_POR_VENCER_INMOBILIARIA,
            cartera_no_devenga=CARTERA_NO_DEVENGA_INMOBILIARIA,
            vencida=VENCIDA_INMOBILIARIA,
            prefijo="morosidad_inmobiliaria",
        )
        mora_micro, componentes_mora_micro = calcular_morosidad(
            saldos,
            cartera_por_vencer=CARTERA_POR_VENCER_MICRO,
            cartera_no_devenga=CARTERA_NO_DEVENGA_MICRO,
            vencida=VENCIDA_MICRO,
            prefijo="morosidad_micro",
        )
        (
            activos_improductivos_netos_sobre_activo,
            componentes_activos_improductivos,
        ) = calcular_activos_improductivos_netos_sobre_activo(saldos)
        (
            cartera_refinanciada_restructurada_sobre_cartera_total,
            cartera_bruta_sobre_activos,
            componentes_cartera,
        ) = calcular_indicadores_cartera(saldos)
        cobertura, componentes_cobertura = calcular_cobertura_cartera_en_riesgo(saldos)

        componentes = {
            **componentes_mora_ampliada,
            **componentes_mora_consumo,
            **componentes_mora_inmobiliaria,
            **componentes_mora_micro,
            **componentes_activos_improductivos,
            **componentes_cartera,
            **componentes_cobertura,
        }

        return CalidadDeActivosResponse(
            fecha_corte=input_data.fecha_corte,
            id_agencia=input_data.id_agencia,
            neteo=1,
            indicadores={
                "morosidad_ampliada": round_ratio(mora_ampliada),
                "morosidad_consumo": round_ratio(mora_consumo),
                "morosidad_inmobiliaria": round_ratio(mora_inmobiliaria),
                "morosidad_micro": round_ratio(mora_micro),
                "activos_improductivos_netos_sobre_activo": round_ratio(
                    activos_improductivos_netos_sobre_activo
                ),
                "cartera_refinanciada_restructurada_sobre_cartera_total": round_ratio(
                    cartera_refinanciada_restructurada_sobre_cartera_total
                ),
                "cartera_bruta_sobre_activos": round_ratio(cartera_bruta_sobre_activos),
                "cobertura_cartera_en_riesgo": round_ratio(cobertura),
            },
            saldos_cuentas={codigo: round_money(valor) for codigo, valor in sorted(saldos.items())},
            componentes={codigo: round_money(valor) for codigo, valor in sorted(componentes.items())},
        )


def obtener_codigos_cuentas_calidad_de_activos() -> list[str]:
    return codigos_unicos(
        (
            CARTERA_POR_VENCER_AMPLIADA,
            CARTERA_NO_DEVENGA_AMPLIADA,
            VENCIDA_AMPLIADA,
            CARTERA_POR_VENCER_CONSUMO,
            CARTERA_NO_DEVENGA_CONSUMO,
            VENCIDA_CONSUMO,
            CARTERA_POR_VENCER_INMOBILIARIA,
            CARTERA_NO_DEVENGA_INMOBILIARIA,
            VENCIDA_INMOBILIARIA,
            CARTERA_POR_VENCER_MICRO,
            CARTERA_NO_DEVENGA_MICRO,
            VENCIDA_MICRO,
            CUENTAS_FONDOS,
            CARTERA_NO_DEVENGA_ACTIVOS_IMPRODUCTIVOS,
            VENCIDA_ACTIVOS_IMPRODUCTIVOS,
            CUENTAS_POR_COBRAR,
            CUENTAS_BIENES_ADJUDICADOS,
            ("18",),
            CUENTAS_OTROS_ACTIVOS,
            CUENTAS_PROVISIONES_IMPRODUCTIVOS,
            CUENTAS_ACTIVO,
            CUENTAS_CARTERA_BRUTA,
            CUENTAS_CARTERA_REFINANCIADA,
            CUENTAS_CARTERA_RESTRUCTURADA,
        )
    )


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


def sumar(saldos: dict[str, float], codigos: Iterable[str]) -> float:
    return sum(float(saldos.get(codigo, 0.0)) for codigo in codigos)


def dividir(numerador: float, denominador: float) -> float | None:
    if denominador == 0:
        return None
    return numerador / denominador


def round_money(valor: float) -> float:
    return round(float(valor or 0.0), 2)


def round_ratio(valor: float | None) -> float | None:
    return round(valor, 6) if valor is not None else None


def calcular_morosidad(
    saldos: dict[str, float],
    *,
    cartera_por_vencer: Iterable[str],
    cartera_no_devenga: Iterable[str],
    vencida: Iterable[str],
    prefijo: str,
) -> tuple[float | None, dict[str, float]]:
    total_por_vencer = sumar(saldos, cartera_por_vencer)
    total_no_devenga = sumar(saldos, cartera_no_devenga)
    total_vencida = sumar(saldos, vencida)
    cartera_en_riesgo = total_vencida + total_no_devenga
    cartera_total = total_por_vencer + cartera_en_riesgo
    componentes = {
        f"{prefijo}_cartera_por_vencer": total_por_vencer,
        f"{prefijo}_cartera_no_devenga": total_no_devenga,
        f"{prefijo}_vencida": total_vencida,
        f"{prefijo}_cartera_en_riesgo": cartera_en_riesgo,
        f"{prefijo}_cartera_total": cartera_total,
    }
    return dividir(cartera_en_riesgo, cartera_total), componentes


def calcular_activos_improductivos_netos_sobre_activo(
    saldos: dict[str, float],
) -> tuple[float | None, dict[str, float]]:
    fondos = saldos.get("11", 0.0) - saldos.get("1103", 0.0)
    cart_no_devenga = sumar(saldos, CARTERA_NO_DEVENGA_ACTIVOS_IMPRODUCTIVOS)
    vencida = sumar(saldos, VENCIDA_ACTIVOS_IMPRODUCTIVOS)
    cuentas_por_cobrar = saldos.get("16", 0.0) - saldos.get("1699", 0.0)
    bienes_adjudicados = (
        saldos.get("17", 0.0)
        - saldos.get("170105", 0.0)
        - saldos.get("170110", 0.0)
        - saldos.get("170115", 0.0)
        + saldos.get("1799", 0.0)
    )
    propiedad_equipo = saldos.get("18", 0.0)
    otros_activos = (
        saldos.get("19", 0.0)
        - saldos.get("1999", 0.0)
        - saldos.get("1901", 0.0)
        - saldos.get("190205", 0.0)
        - saldos.get("190210", 0.0)
        - saldos.get("190215", 0.0)
        - saldos.get("190220", 0.0)
        - saldos.get("190240", 0.0)
        - saldos.get("190250", 0.0)
        - saldos.get("190280", 0.0)
        - saldos.get("190286", 0.0)
        - saldos.get("1903", 0.0)
    )
    total_improductivos_brutos = (
        otros_activos
        + propiedad_equipo
        + bienes_adjudicados
        + cuentas_por_cobrar
        + vencida
        + cart_no_devenga
        + fondos
    )
    provisiones = sumar(saldos, CUENTAS_PROVISIONES_IMPRODUCTIVOS)
    total_improductivos_netos = total_improductivos_brutos + provisiones
    activos = saldos.get("1", 0.0)
    componentes = {
        "activos_improductivos_fondos": fondos,
        "activos_improductivos_cartera_no_devenga": cart_no_devenga,
        "activos_improductivos_vencida": vencida,
        "activos_improductivos_cuentas_por_cobrar": cuentas_por_cobrar,
        "activos_improductivos_bienes_adjudicados": bienes_adjudicados,
        "activos_improductivos_propiedad_equipo": propiedad_equipo,
        "activos_improductivos_otros_activos": otros_activos,
        "activos_improductivos_brutos": total_improductivos_brutos,
        "activos_improductivos_provisiones": provisiones,
        "activos_improductivos_netos": total_improductivos_netos,
        "activos_total": activos,
    }
    return dividir(total_improductivos_netos, activos), componentes


def calcular_indicadores_cartera(
    saldos: dict[str, float],
) -> tuple[float | None, float | None, dict[str, float]]:
    cartera_bruta = saldos.get("14", 0.0) - saldos.get("1499", 0.0)
    activos = saldos.get("1", 0.0)
    cartera_refinanciada = sumar(saldos, CUENTAS_CARTERA_REFINANCIADA)
    cartera_restructurada = sumar(saldos, CUENTAS_CARTERA_RESTRUCTURADA)
    cartera_refinanciada_restructurada = cartera_refinanciada + cartera_restructurada
    componentes = {
        "cartera_bruta": cartera_bruta,
        "cartera_bruta_activos": activos,
        "cartera_refinanciada": cartera_refinanciada,
        "cartera_restructurada": cartera_restructurada,
        "cartera_refinanciada_restructurada": cartera_refinanciada_restructurada,
    }
    return (
        dividir(cartera_refinanciada_restructurada, cartera_bruta),
        dividir(cartera_bruta, activos),
        componentes,
    )


def calcular_cobertura_cartera_en_riesgo(
    saldos: dict[str, float],
) -> tuple[float, dict[str, float]]:
    cart_no_devenga = sumar(saldos, CARTERA_NO_DEVENGA_AMPLIADA)
    vencida = sumar(saldos, VENCIDA_AMPLIADA)
    cartera_en_riesgo = vencida + cart_no_devenga
    provision = abs(saldos.get("1499", 0.0))
    cobertura = provision / cartera_en_riesgo if cartera_en_riesgo != 0 else 0.0
    componentes = {
        "cobertura_cartera_no_devenga": cart_no_devenga,
        "cobertura_vencida": vencida,
        "cobertura_cartera_en_riesgo": cartera_en_riesgo,
        "cobertura_provision": provision,
    }
    return cobertura, componentes

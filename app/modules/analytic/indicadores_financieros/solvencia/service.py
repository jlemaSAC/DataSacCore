from datetime import date, datetime, time
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from fastapi import HTTPException

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
from app.modules.analytic.indicadores_financieros.solvencia.repositories.mongo_solvencia_repository import (
    MongoIndicadoresFinancierosRepository,
)
from app.modules.analytic.indicadores_financieros.solvencia.repositories.sql_solvencia_repository import (
    SqlIndicadoresFinancierosRepository,
    to_float,
)
from app.modules.analytic.indicadores_financieros.solvencia.schemas import (
    InputSolvencia,
    InputSolvenciaHistorico,
    SolvenciaHistoricoItem,
    SolvenciaHistoricoResponse,
    SolvenciaResponse,
)


CUENTAS_PTC_PRIMARIO = ("31", "3301", "3303", "34", "3602", "3604", "330115")
CUENTAS_PTC_SECUNDARIO = ("2801", "3305", "35", "3601", "3603", "149989")
CUENTAS_UTILIDAD = ("4", "5")
CUENTAS_PROVISION_CONSTITUIDA = ("1499", "149980", "149989")
CUENTAS_PATRIMONIO_SOBRE_ACTIVO = ("1", "3")
CUENTAS_ACTIVOS_IMPRODUCTIVOS_NETOS = (
    "11",
    "1103",
    "1425",
    "1426",
    "1427",
    "1428",
    "1429",
    "1430",
    "1432",
    "1433",
    "1434",
    "1435",
    "1436",
    "1437",
    "1438",
    "1440",
    "1441",
    "1442",
    "1443",
    "1444",
    "1445",
    "1446",
    "1448",
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
    "1464",
    "1465",
    "1466",
    "1467",
    "1468",
    "1469",
    "1470",
    "1472",
    "1479",
    "1481",
    "1483",
    "1485",
    "1487",
    "1489",
    "16",
    "17",
    "18",
    "19",
    "1901",
    "190205",
    "190215",
    "190220",
    "190240",
    "190280",
    "190286",
    "1908",
    "1499",
)

CUENTAS_RIESGO_CERO = ("11", "1302", "1304", "1306", "199005", "190286", "16404", "640410", "7108")
CUENTAS_RIESGO_VEINTE = ("12", "1307")
CUENTAS_RIESGO_CINCUENTA = ("1301", "1303", "1305", "1403", "1408", "1619", "640505")
CUENTAS_RIESGO_CIEN_BASE = ("13", "14", "16", "17", "18", "19", "64")
CUENTAS_RIESGO_CIEN_RESTAS = (
    "1301",
    "1303",
    "1305",
    "1307",
    "1302",
    "1304",
    "1306",
    "1403",
    "1408",
    "1407",
    "1415",
    "1423",
    "1431",
    "1439",
    "1447",
    "1455",
    "1463",
    "1471",
    "7108",
    "1619",
    "199005",
    "190286",
    "640505",
    "16404",
)
CUENTAS_RIESGO_DOSCIENTOS = ("1407", "1415", "1423", "1431", "1439", "1447", "1455", "1463", "1471")

TIMEZONE_ECUADOR = ZoneInfo("America/Guayaquil")
INDICADORES_SOLVENCIA_HISTORICO = (
    "solvencia",
    "activos_fijos_sobre_patrimonio_tecnico",
    "patrimonio_sobre_activo",
    "patrimonio_resultados_sobre_activos_improductivos_netos",
)


class IndicadoresFinancierosService:
    def __init__(
        self,
        saldo_contable_repository: SqlSaldoContableRepository,
        sql_repository: SqlIndicadoresFinancierosRepository,
        mongo_repository: MongoIndicadoresFinancierosRepository,
    ) -> None:
        self.saldo_contable_repository = saldo_contable_repository
        self.sql_repository = sql_repository
        self.mongo_repository = mongo_repository

    def calcular_solvencia(
        self,
        input_data: InputSolvencia,
        auth_context: AuthContext,
    ) -> SolvenciaResponse:
        _ = auth_context
        try:
            codigos = obtener_codigos_cuentas_solvencia()
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

            return self._calcular_solvencia_desde_saldos(input_data=input_data, saldos=saldos)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando solvencia: {exc}",
            ) from exc

    def consultar_solvencia_historico_mensual(
        self,
        input_data: InputSolvenciaHistorico,
        auth_context: AuthContext,
    ) -> SolvenciaHistoricoResponse:
        _ = auth_context
        try:
            fechas_consulta = construir_fechas_consulta_mensual(
                periodo_desde=input_data.periodo_desde,
                periodo_hasta=input_data.periodo_hasta,
                hoy=fecha_actual_ecuador(),
            )
            return self._consultar_solvencia_por_fechas(
                input_data=input_data,
                fechas_consulta=fechas_consulta,
                formato_sin_datos="%Y-%m",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando historico mensual de solvencia: {exc}",
            ) from exc

    def consultar_solvencia_historico_diario(
        self,
        input_data: InputSolvenciaHistorico,
        auth_context: AuthContext,
    ) -> SolvenciaHistoricoResponse:
        _ = auth_context
        try:
            fechas_consulta = construir_fechas_consulta_diaria(
                periodo_desde=input_data.periodo_desde,
                periodo_hasta=input_data.periodo_hasta,
                hoy=fecha_actual_ecuador(),
            )
            return self._consultar_solvencia_por_fechas(
                input_data=input_data,
                fechas_consulta=fechas_consulta,
                formato_sin_datos="%Y-%m-%d",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculando historico diario de solvencia: {exc}",
            ) from exc

    def _consultar_solvencia_por_fechas(
        self,
        *,
        input_data: InputSolvenciaHistorico,
        fechas_consulta: list[date],
        formato_sin_datos: str,
    ) -> SolvenciaHistoricoResponse:
        codigos = obtener_codigos_cuentas_solvencia()
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
        datos: list[SolvenciaHistoricoItem] = []
        periodos_sin_datos: list[str] = []

        for fecha_corte in fechas_consulta:
            saldos = saldos_por_fecha.get(fecha_corte)
            if not saldos:
                periodos_sin_datos.append(fecha_corte.strftime(formato_sin_datos))
                continue

            for codigo in codigos:
                saldos.setdefault(codigo, 0.0)
            try:
                resultado = self._calcular_solvencia_desde_saldos(
                    input_data=InputSolvencia(
                        fecha_corte=datetime.combine(fecha_corte, time.min),
                        id_agencia=input_data.id_agencia,
                    ),
                    saldos=saldos,
                )
            except HTTPException as exc:
                if not es_error_situacion_crediticia_sin_datos(exc):
                    raise
                periodos_sin_datos.append(fecha_corte.strftime(formato_sin_datos))
                continue

            valores = {
                nombre: resultado.indicadores.get(nombre)
                for nombre in INDICADORES_SOLVENCIA_HISTORICO
            }
            datos.append(
                SolvenciaHistoricoItem(
                    fecha_corte=fecha_corte,
                    anio=fecha_corte.year,
                    mes=fecha_corte.month,
                    dia=fecha_corte.day,
                    **valores,
                )
            )

        return SolvenciaHistoricoResponse(
            id_agencia=input_data.id_agencia,
            periodo_desde=input_data.periodo_desde,
            periodo_hasta=input_data.periodo_hasta,
            neteo=1,
            datos=datos,
            periodos_sin_datos=periodos_sin_datos,
        )

    def _calcular_solvencia_desde_saldos(
        self,
        *,
        input_data: InputSolvencia,
        saldos: dict[str, float],
    ) -> SolvenciaResponse:
        mes = input_data.fecha_corte.month
        utilidad = calcular_utilidad(saldos)
        deficiencia_info = self.calcular_deficiencia(input_data=input_data, saldos=saldos)
        deficiencia = float(deficiencia_info.get("deficiencia") or 0.0)
        ptc_primario, componentes_primario = calcular_patrimonio_tecnico_primario(
            saldos,
            mes=mes,
            utilidad=utilidad,
        )
        ptc_secundario, componentes_secundario = calcular_patrimonio_tecnico_secundario(
            saldos,
            mes=mes,
            utilidad=utilidad,
            deficiencia=deficiencia,
        )
        patrimonio_tecnico_constituido = ptc_primario + ptc_secundario
        activos_fijos_sobre_patrimonio_tecnico = (
            saldos.get("18", 0.0) / patrimonio_tecnico_constituido
            if patrimonio_tecnico_constituido != 0
            else None
        )
        patrimonio_sobre_activo = (
            saldos.get("3", 0.0) / saldos.get("1", 0.0)
            if saldos.get("1", 0.0) != 0
            else None
        )
        activos_improductivos_netos = calcular_activos_improductivos_netos(saldos)
        patrimonio_resultados_sobre_activos_improductivos_netos = (
            (saldos.get("3", 0.0) + utilidad) / activos_improductivos_netos
            if activos_improductivos_netos != 0
            else None
        )
        activos_ponderados, componentes_riesgo = calcular_activos_ponderados_por_riesgo(saldos)
        solvencia = (
            patrimonio_tecnico_constituido / activos_ponderados
            if activos_ponderados != 0
            else None
        )
        componentes = {
            **componentes_primario,
            **componentes_secundario,
            **componentes_riesgo,
        }

        return SolvenciaResponse(
            fecha_corte=input_data.fecha_corte,
            id_agencia=input_data.id_agencia,
            neteo=1,
            mes=mes,
            deficiencia=round_money(deficiencia),
            deficiencia_fuente=str(deficiencia_info.get("fuente") or ""),
            provision_requerida=round_money(deficiencia_info.get("provision_requerida") or 0.0),
            provision_constituida=round_money(deficiencia_info.get("provision_constituida") or 0.0),
            utilidad=round_money(utilidad),
            patrimonio_tecnico_primario=round_money(ptc_primario),
            patrimonio_tecnico_secundario=round_money(ptc_secundario),
            patrimonio_tecnico_constituido=round_money(patrimonio_tecnico_constituido),
            activos_improductivos_netos=round_money(activos_improductivos_netos),
            activos_ponderados_por_riesgo=round_money(activos_ponderados),
            indicadores={
                "solvencia": round(solvencia, 6) if solvencia is not None else None,
                "activos_fijos_sobre_patrimonio_tecnico": (
                    round(activos_fijos_sobre_patrimonio_tecnico, 6)
                    if activos_fijos_sobre_patrimonio_tecnico is not None
                    else None
                ),
                "patrimonio_sobre_activo": (
                    round(patrimonio_sobre_activo, 6)
                    if patrimonio_sobre_activo is not None
                    else None
                ),
                "patrimonio_resultados_sobre_activos_improductivos_netos": (
                    round(patrimonio_resultados_sobre_activos_improductivos_netos, 6)
                    if patrimonio_resultados_sobre_activos_improductivos_netos is not None
                    else None
                ),
            },
            saldos_cuentas={codigo: round_money(valor) for codigo, valor in sorted(saldos.items())},
            componentes={codigo: round_money(valor) for codigo, valor in sorted(componentes.items())},
        )

    def calcular_deficiencia(
        self,
        *,
        input_data: InputSolvencia,
        saldos: dict[str, float],
    ) -> dict[str, Any]:
        provision_constituida = calcular_provision_constituida_contable(saldos)

        if input_data.deficiencia is not None:
            return {
                "deficiencia": max(float(input_data.deficiencia or 0.0), 0.0),
                "fuente": "manual",
                "provision_requerida": 0.0,
                "provision_constituida": provision_constituida,
            }

        hoy = datetime.now(TIMEZONE_ECUADOR).date()
        fecha_corte = input_data.fecha_corte.date()

        if fecha_corte > hoy:
            raise HTTPException(
                status_code=400,
                detail="No se puede calcular deficiencia automaticamente para fechas futuras.",
            )

        if fecha_corte == hoy:
            fecha_consulta = datetime.now(TIMEZONE_ECUADOR).replace(tzinfo=None)
            info = self.calcular_deficiencia_sql_vivo(
                fecha_consulta=fecha_consulta,
                id_agencia=input_data.id_agencia,
            )
        else:
            info = self.calcular_deficiencia_mongo(
                fecha_corte=input_data.fecha_corte,
                id_agencia=input_data.id_agencia,
            )

        info["provision_constituida"] = provision_constituida
        info["deficiencia"] = deficiencia_desde_diferencia(
            to_float(info.get("provision_requerida")),
            provision_constituida,
        )
        return info

    def calcular_deficiencia_mongo(
        self,
        *,
        fecha_corte: datetime,
        id_agencia: int,
    ) -> dict[str, Any]:
        nombre_agencia = self.sql_repository.get_nombre_agencia(id_agencia)
        provision_requerida = self.mongo_repository.get_provision_requerida_situacion_crediticia(
            fecha_corte=fecha_corte,
            nombre_agencia=nombre_agencia,
        )
        return {
            "deficiencia": 0.0,
            "fuente": "mongo_situacion_crediticia",
            "provision_requerida": provision_requerida,
            "provision_constituida": 0.0,
        }

    def calcular_deficiencia_sql_vivo(
        self,
        *,
        fecha_consulta: datetime,
        id_agencia: int,
    ) -> dict[str, Any]:
        ids_prestamos = self.sql_repository.get_ids_prestamos_activos(id_agencia)
        provision_requerida = self.sql_repository.sum_provision_requerida_viva(
            ids_prestamos=ids_prestamos,
            fecha_consulta=fecha_consulta,
        )
        return {
            "deficiencia": 0.0,
            "fuente": "sql_vivo_provisiones",
            "provision_requerida": provision_requerida,
            "provision_constituida": 0.0,
        }


def obtener_codigos_cuentas_solvencia() -> list[str]:
    return codigos_unicos(
        (
            CUENTAS_PTC_PRIMARIO,
            CUENTAS_PTC_SECUNDARIO,
            CUENTAS_UTILIDAD,
            CUENTAS_PROVISION_CONSTITUIDA,
            CUENTAS_PATRIMONIO_SOBRE_ACTIVO,
            CUENTAS_ACTIVOS_IMPRODUCTIVOS_NETOS,
            CUENTAS_RIESGO_CERO,
            CUENTAS_RIESGO_VEINTE,
            CUENTAS_RIESGO_CINCUENTA,
            CUENTAS_RIESGO_CIEN_BASE,
            CUENTAS_RIESGO_CIEN_RESTAS,
            CUENTAS_RIESGO_DOSCIENTOS,
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


def es_error_situacion_crediticia_sin_datos(exc: HTTPException) -> bool:
    return exc.status_code == 422 and "No hay datos en SituacionCrediticia" in str(exc.detail)


def round_money(valor: float) -> float:
    return round(float(valor or 0.0), 2)


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


def deficiencia_desde_diferencia(
    provision_requerida: float,
    provision_constituida: float,
) -> float:
    return max(provision_requerida - provision_constituida, 0.0)


def calcular_provision_constituida_contable(saldos: dict[str, float]) -> float:
    return (
        abs(saldos.get("1499", 0.0))
        - abs(saldos.get("149980", 0.0))
        - abs(saldos.get("149989", 0.0))
    )


def calcular_utilidad(saldos: dict[str, float]) -> float:
    return float(saldos.get("5", 0.0)) - float(saldos.get("4", 0.0))


def calcular_patrimonio_tecnico_primario(
    saldos: dict[str, float],
    *,
    mes: int,
    utilidad: float,
) -> tuple[float, dict[str, float]]:
    utilidad_aplicada = utilidad if mes < 12 and utilidad < 0 else 0.0
    componentes = {
        "ptc_primario_31": saldos.get("31", 0.0),
        "ptc_primario_3301": saldos.get("3301", 0.0),
        "ptc_primario_3303": saldos.get("3303", 0.0),
        "ptc_primario_34": saldos.get("34", 0.0),
        "ptc_primario_3602": saldos.get("3602", 0.0),
        "ptc_primario_3604": saldos.get("3604", 0.0),
        "ptc_primario_330115": saldos.get("330115", 0.0),
        "ptc_primario_utilidad": utilidad_aplicada,
    }
    return sum(componentes.values()), componentes


def calcular_patrimonio_tecnico_secundario(
    saldos: dict[str, float],
    *,
    mes: int,
    utilidad: float,
    deficiencia: float,
) -> tuple[float, dict[str, float]]:
    utilidad_aplicada = utilidad * 0.5 if mes < 12 and utilidad > 0 else 0.0
    componentes = {
        "ptc_secundario_2801": saldos.get("2801", 0.0),
        "ptc_secundario_3305_50": saldos.get("3305", 0.0) * 0.5,
        "ptc_secundario_35_45": saldos.get("35", 0.0) * 0.45,
        "ptc_secundario_3601": saldos.get("3601", 0.0),
        "ptc_secundario_3603": saldos.get("3603", 0.0),
        "ptc_secundario_149989_abs": abs(saldos.get("149989", 0.0)),
        "ptc_secundario_utilidad": utilidad_aplicada,
        "ptc_secundario_deficiencia": -float(deficiencia or 0.0),
    }
    return sum(componentes.values()), componentes


def calcular_activos_ponderados_por_riesgo(
    saldos: dict[str, float],
) -> tuple[float, dict[str, float]]:
    cero = sumar(saldos, CUENTAS_RIESGO_CERO) * 0
    veinte = sumar(saldos, CUENTAS_RIESGO_VEINTE) * 0.2
    cincuenta = sumar(saldos, CUENTAS_RIESGO_CINCUENTA) * 0.5
    cien = sumar(saldos, CUENTAS_RIESGO_CIEN_BASE) - sumar(saldos, CUENTAS_RIESGO_CIEN_RESTAS)
    doscientos = sumar(saldos, CUENTAS_RIESGO_DOSCIENTOS) * 2
    componentes = {
        "activos_riesgo_0": cero,
        "activos_riesgo_20": veinte,
        "activos_riesgo_50": cincuenta,
        "activos_riesgo_100": cien,
        "activos_riesgo_200": doscientos,
    }
    return sum(componentes.values()), componentes


def calcular_activos_improductivos_netos(saldos: dict[str, float]) -> float:
    fondos = saldos.get("11", 0.0) - saldos.get("1103", 0.0)
    cart_no_deven = sumar(
        saldos,
        (
            "1425",
            "1426",
            "1427",
            "1428",
            "1429",
            "1430",
            "1432",
            "1433",
            "1434",
            "1435",
            "1436",
            "1437",
            "1438",
            "1440",
            "1441",
            "1442",
            "1443",
            "1444",
            "1445",
            "1446",
            "1448",
        ),
    )
    vencida = sumar(
        saldos,
        (
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
            "1464",
            "1465",
            "1466",
            "1467",
            "1468",
            "1469",
            "1470",
            "1472",
            "1479",
            "1481",
            "1483",
            "1485",
            "1487",
            "1489",
        ),
    )
    return (
        fondos
        + vencida
        + cart_no_deven
        + saldos.get("1499", 0.0)
        + saldos.get("16", 0.0)
        + saldos.get("17", 0.0)
        + saldos.get("18", 0.0)
        + saldos.get("19", 0.0)
        - saldos.get("1901", 0.0)
        - saldos.get("190205", 0.0)
        - saldos.get("190215", 0.0)
        - saldos.get("190220", 0.0)
        - saldos.get("190240", 0.0)
        - saldos.get("190280", 0.0)
        - saldos.get("190286", 0.0)
        - saldos.get("1908", 0.0)
    )

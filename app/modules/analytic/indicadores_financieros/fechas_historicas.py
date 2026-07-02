from calendar import monthrange
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException


TIMEZONE_ECUADOR = ZoneInfo("America/Guayaquil")
MAX_FECHAS_POR_CONSULTA = 1000


def fecha_actual_ecuador() -> date:
    return datetime.now(TIMEZONE_ECUADOR).date()


def construir_fechas_consulta_mensual(
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

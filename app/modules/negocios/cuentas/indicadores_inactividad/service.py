from collections.abc import Iterable, Mapping
from decimal import Decimal, localcontext
from typing import Any

from app.modules.auth.schemas import AuthContext

from ..resumen import fecha_de_sistema, ids_agencia
from .constantes import RANGOS_EDAD
from .repositories.sql_indicadores_inactividad_repository import SqlIndicadoresInactividadRepository
from .schemas import (
    DimensionInactividad,
    Estadisticas,
    GrupoInactividad,
    IndicadoresGenerales,
    IndicadoresInactividadRequest,
    IndicadoresInactividadResponse,
)


_DIMENSIONES: tuple[DimensionInactividad, ...] = (
    "rango_edad", "sexo", "estado_civil", "socio", "agencia", "anio", "mes_agencia", "mes_apertura",
)
_EDADES = {0: "No especificado", **{inicio: f"De {inicio} a {fin} años" for inicio, fin in RANGOS_EDAD}}


def _porcentaje(cantidad: int, universo: int) -> float | None:
    return round(cantidad * 100 / universo, 4) if universo else None


def _estadisticas(
    cantidad: int, promedio: float | None, maximo: int | None, minimo: int | None,
) -> Estadisticas:
    return Estadisticas(
        cuentas_con_dato=cantidad, promedio=promedio, maximo=maximo, minimo=minimo,
        rango=maximo - minimo if maximo is not None and minimo is not None else None,
    )


def _agrupar(
    filas: Iterable[Mapping[str, Any]], positivas: int,
) -> dict[DimensionInactividad, list[GrupoInactividad]]:
    dimensiones: dict[DimensionInactividad, list[GrupoInactividad]] = {d: [] for d in _DIMENSIONES}
    if not positivas:
        return dimensiones

    edades = dict.fromkeys(_EDADES, 0)
    for fila in filas:
        dimension = fila["dimension"]
        if dimension == "total":
            continue
        cantidad = fila["cuentas_positivas"]
        if dimension == "rango_edad":
            edades[fila["rango_edad"]] = cantidad
            continue
        id_agencia = fila["id_agencia"]
        periodo = fila["mes"] if dimension == "mes_agencia" else fila.get(dimension)
        nombre = str(periodo) if periodo is not None else "No especificado"
        clave = str(periodo) if periodo is not None else ""
        if dimension == "agencia":
            clave, nombre = str(id_agencia), fila["agencia"]
        elif dimension == "mes_agencia":
            clave = f"{clave}:{id_agencia}"
        dimensiones[dimension].append(GrupoInactividad(
            clave=clave, nombre=nombre, id_agencia=id_agencia,
            agencia=fila["agencia"], cantidad=cantidad,
            porcentaje=round(cantidad * 100 / positivas, 4),
        ))

    dimensiones["rango_edad"] = [
        GrupoInactividad(
            clave=str(clave), nombre=nombre, cantidad=edades[clave],
            porcentaje=round(edades[clave] * 100 / positivas, 4),
        )
        for clave, nombre in _EDADES.items()
    ]
    for dimension in ("sexo", "estado_civil", "socio", "agencia"):
        dimensiones[dimension].sort(key=lambda grupo: (-grupo.cantidad, grupo.nombre, grupo.clave))
    for dimension in ("anio", "mes_agencia", "mes_apertura"):
        dimensiones[dimension].sort(
            key=lambda grupo: (
                grupo.nombre if grupo.clave.partition(":")[0] else "",
                grupo.cantidad, grupo.agencia or "", grupo.clave,
            ),
            reverse=True,
        )
    return dimensiones


class IndicadoresInactividadService:
    def __init__(self, repositorio: SqlIndicadoresInactividadRepository) -> None:
        self.repositorio = repositorio

    def consultar(
        self, body: IndicadoresInactividadRequest, auth: AuthContext,
    ) -> IndicadoresInactividadResponse:
        fecha_sistema = fecha_de_sistema(auth)
        incluir_analisis = body.condicion_saldo != "cero"
        filas = self.repositorio.obtener_indicadores(
            ids_agencia=ids_agencia(body), fecha_sistema=fecha_sistema,
            incluir_analisis=incluir_analisis,
        )
        total = next(fila for fila in filas if fila["dimension"] == "total")
        brutas, positivas = total["cuentas_brutas"], total["cuentas_positivas"]
        cero = total["cuentas_cero"]
        seleccionadas = {
            "todas": brutas, "cero": cero, "positivo": positivas,
        }[body.condicion_saldo]

        # Reutilizar los importes de la agrupación ya calculada para la dimensión socio.
        saldos_por_socio = {
            fila["socio"]: fila["saldo_total"]
            for fila in filas
            if incluir_analisis and fila["dimension"] == "socio"
        }

        saldo_restante = Decimal(0)
        if positivas > 2:
            # El gráfico separa dos cuentas y conserva la precisión del saldo agregado.
            with localcontext() as contexto:
                contexto.prec = 38
                saldo_restante = total["saldo_total"] - total["saldo_maximo"] - total["saldo_minimo"]

        return IndicadoresInactividadResponse(
            id_agencia=body.id_agencia, fecha_corte=fecha_sistema, condicion_saldo=body.condicion_saldo,
            generales=IndicadoresGenerales(
                cuentas_brutas=brutas, cuentas_cero=cero, cuentas_positivas=positivas,
                cuentas_seleccionadas=seleccionadas,
                porcentaje_base_bruta=_porcentaje(brutas, brutas),
                porcentaje_con_saldo=_porcentaje(positivas, brutas),
                saldo_total=total["saldo_total"],
                saldo_socios=saldos_por_socio.get("Socio", Decimal(0)),
                saldo_no_socios=saldos_por_socio.get("No socio", Decimal(0)),
                saldo_socio_no_especificado=saldos_por_socio.get(None, Decimal(0)),
                saldo_maximo=total["saldo_maximo"],
                saldo_minimo=total["saldo_minimo"], saldo_restante=saldo_restante,
            ),
            inactividad=_estadisticas(
                total["cuentas_con_inactivacion"], total["inactivacion_promedio"],
                total["inactivacion_maximo"], total["inactivacion_minimo"],
            ) if incluir_analisis else None,
            ultima_transaccion_activa=_estadisticas(
                total["cuentas_con_dias"], total["dias_promedio"],
                total["dias_maximo"], total["dias_minimo"],
            ) if incluir_analisis else None,
            dimensiones=_agrupar(filas, positivas if incluir_analisis else 0),
        )

from datetime import date, datetime

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)

from .schemas import AgenciasConsulta, IndicadoresCuentas, ResumenAgencia, ResumenOficialTipoCuenta


def resumir_por_agencia(
    desglose: list[ResumenOficialTipoCuenta], catalogo: SqlSituacionCrediticiaAsesoresRepository,
) -> tuple[list[ResumenAgencia], IndicadoresCuentas | None]:
    responsables = {
        fila["IdAgencia"]: fila
        for fila in catalogo.obtener_gerentes_oficina({fila.agencia for fila in desglose})
    }
    resumen: dict[int, ResumenAgencia] = {}
    total: IndicadoresCuentas | None = None
    for fila in desglose:
        clave = fila.id_agencia
        if clave not in resumen:
            responsable = responsables.get(fila.id_agencia, {})
            resumen[clave] = ResumenAgencia.model_validate({
                **fila.model_dump(),
                "cargo_jefe_agencia": responsable.get("Cargo"),
                "nombre_jefe_agencia": responsable.get("GerenteOficina"),
            })
        else:
            _acumular(resumen[clave], fila)
        if total is None:
            total = IndicadoresCuentas.model_validate(fila.model_dump())
        else:
            _acumular(total, fila)
    return list(resumen.values()), total


def ids_agencia(body: AgenciasConsulta) -> list[int]:
    return sorted(set(body.ids_agencia)) if body.id_agencia == 0 else [body.id_agencia]


def _acumular(acumulado: IndicadoresCuentas, fila: IndicadoresCuentas) -> None:
    acumulado.cantidad_cuentas += fila.cantidad_cuentas
    acumulado.valor_disponible += fila.valor_disponible
    acumulado.valor_total += fila.valor_total


def fecha_de_sistema(auth: AuthContext) -> date:
    fecha = auth.usuario.fecha_sistema
    return fecha.date() if isinstance(fecha, datetime) else fecha

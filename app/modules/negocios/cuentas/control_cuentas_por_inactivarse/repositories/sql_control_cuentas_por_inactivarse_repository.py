from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ...schemas import FiltroSaldo
from ...sql_cuentas import (
    AGENCIA_EXPANDIBLE,
    CARGO_OFICIAL,
    NOMBRE_CARGO,
    PREDICADOS_SALDO,
    RESUMEN,
    SALDOS_POR_CUENTA,
    TABLAS_CUENTA_BASE,
    TITULAR_PRINCIPAL,
    filtros_detalle,
)
from ..schemas import PlazoInactivacion


_RANGOS_PLAZO = {
    "cumplido": (None, -1),
    "0_7": (0, 7),
    "8_15": (8, 15),
    "16_30": (16, 30),
}

# El cierre cambia el estado cuando DATEDIFF(day, última actividad, cierre)
# es estrictamente mayor que el plazo configurado para el tipo de cuenta.
_FECHA_CUMPLIMIENTO = """
    DATEADD(day, D.DIASINACTIVIDAD + 1, CAST(C.FECHAULTIMATRANSACCIONACTIVA AS date))
"""

_CANDIDATAS = """
    CuentasCandidatas AS (
        SELECT C.NUMERO, C.IDAGENCIA, C.CODIGOUSUARIOOFICIAL, C.CODIGOTIPOCUENTA,
               TC.NOMBRE AS tipo_cuenta, C.FECHAULTIMATRANSACCIONACTIVA,
               P.fecha_cumplimiento
        {tablas_cuenta}
        INNER JOIN AHORROS.TIPO_CUENTA_DIASINACTIVA AS D
            ON D.CODIGOTIPOCUENTA = C.CODIGOTIPOCUENTA
        CROSS APPLY (VALUES ({fecha_cumplimiento})) AS P(fecha_cumplimiento)
        {fuente_cargo}
        WHERE C.CODIGOESTADO = N'A'
          AND C.IDAGENCIA IN :ids_agencia
          AND TC.ESCERTIFICADOAPORTACION = 0
          AND ({filtro_plazo})
          {filtros_seleccion}
    )
"""


def _cuentas_candidatas(
    params: dict[str, Any], fecha_sistema: date, plazos: list[PlazoInactivacion],
    *, fuente_cargo: str = "", filtros_seleccion: str = "",
) -> str:
    if not plazos:
        filtro_plazo = "P.fecha_cumplimiento <= :hasta"
        params["hasta"] = fecha_sistema + timedelta(days=30)
    else:
        condiciones = []
        for indice, plazo in enumerate(dict.fromkeys(plazos)):
            minimo, maximo = _RANGOS_PLAZO[plazo]
            hasta = f"hasta_{indice}"
            condicion = f"P.fecha_cumplimiento <= :{hasta}"
            params[hasta] = fecha_sistema + timedelta(days=maximo)
            if minimo is not None:
                desde = f"desde_{indice}"
                condicion += f" AND P.fecha_cumplimiento >= :{desde}"
                params[desde] = fecha_sistema + timedelta(days=minimo)
            condiciones.append(f"({condicion})")
        filtro_plazo = " OR ".join(condiciones)
    return _CANDIDATAS.format(
        tablas_cuenta=TABLAS_CUENTA_BASE, fecha_cumplimiento=_FECHA_CUMPLIMIENTO,
        fuente_cargo=fuente_cargo, filtros_seleccion=filtros_seleccion, filtro_plazo=filtro_plazo,
    )


class SqlControlCuentasPorInactivarseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_desglose(
        self, ids_agencia: list[int], *, fecha_sistema: date,
        plazos: list[PlazoInactivacion], saldo: FiltroSaldo | None,
    ) -> Sequence[Mapping[str, Any]]:
        params: dict[str, Any] = {"ids_agencia": ids_agencia}
        consulta = text(RESUMEN.format(
            ctes_cuentas=_cuentas_candidatas(params, fecha_sistema, plazos),
            fuente_cuentas="CuentasCandidatas", saldos_por_cuenta=SALDOS_POR_CUENTA,
            predicado_saldo=PREDICADOS_SALDO[saldo], valor_total_cuenta="COALESCE(S.total, 0)",
            nombre_cargo=NOMBRE_CARGO, cargo_oficial=CARGO_OFICIAL.format(usuario="X.codigo_oficial"),
        )).bindparams(AGENCIA_EXPANDIBLE)
        return self.db.execute(consulta, params).mappings().all()

    def obtener_detalle(
        self, *, ids_agencia: list[int], fecha_sistema: date,
        plazos: list[PlazoInactivacion], saldo: FiltroSaldo | None,
        cargos: list[str], asesores: list[str], codigo_oficial: str | None,
        codigo_tipo_cuenta: str | None, pagina: int, tamano_pagina: int, sin_paginacion: bool,
    ) -> tuple[int, Sequence[Mapping[str, Any]]]:
        params: dict[str, Any] = {"ids_agencia": ids_agencia}
        fuente_cargo, filtros_seleccion, expandibles = filtros_detalle(
            params, codigo_oficial=codigo_oficial, codigo_tipo_cuenta=codigo_tipo_cuenta,
            cargos=cargos, asesores=asesores,
        )
        candidatas = _cuentas_candidatas(
            params, fecha_sistema, plazos, fuente_cargo=fuente_cargo,
            filtros_seleccion=filtros_seleccion,
        )
        predicado_saldo = PREDICADOS_SALDO[saldo]
        fuente = """
            FROM CuentasCandidatas AS C
            INNER JOIN GENERAL.AGENCIA AS A ON A.ID = C.IDAGENCIA
            INNER JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = C.CODIGOUSUARIOOFICIAL
        """
        orden = "ORDER BY COALESCE(S.total, 0) DESC, C.NUMERO"
        total = 0
        if not sin_paginacion:
            saldos_conteo = SALDOS_POR_CUENTA if predicado_saldo else ""
            conteo = text(f"""
                WITH {candidatas}
                SELECT COUNT_BIG(*) {fuente}
                {saldos_conteo}
                WHERE 1 = 1 {predicado_saldo}
            """).bindparams(*expandibles)
            total = self.db.execute(conteo, params).scalar_one()
            desplazamiento = (pagina - 1) * tamano_pagina
            if desplazamiento >= total:
                return total, []
            orden += " OFFSET :desplazamiento ROWS FETCH NEXT :limite ROWS ONLY"
            params.update(desplazamiento=desplazamiento, limite=tamano_pagina)
        consulta = text(f"""
            WITH {candidatas}
            SELECT C.NUMERO AS numero_cuenta, A.NOMBRE AS agencia, U.NOMBRE AS oficial,
                   C.tipo_cuenta, T.titular,
                   CAST(C.FECHAULTIMATRANSACCIONACTIVA AS date) AS ultima_transaccion_activa,
                   C.fecha_cumplimiento,
                   DATEDIFF(day, :fecha_sistema, C.fecha_cumplimiento) AS dias_restantes,
                   COALESCE(S.disponible, 0) AS valor_disponible,
                   COALESCE(S.total, 0) AS valor_total
            {fuente}
            {SALDOS_POR_CUENTA}
            {TITULAR_PRINCIPAL}
            WHERE 1 = 1 {predicado_saldo}
            {orden}
        """).bindparams(*expandibles)
        filas = self.db.execute(consulta, {**params, "fecha_sistema": fecha_sistema}).mappings().all()
        return (len(filas) if sin_paginacion else total), filas

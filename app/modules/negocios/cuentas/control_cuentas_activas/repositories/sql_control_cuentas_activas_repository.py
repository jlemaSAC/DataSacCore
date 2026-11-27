from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from ...sql_cuentas import (
    AGENCIA_EXPANDIBLE, CARGO_OFICIAL, ESTADO_RESULTANTE, NOMBRE_CARGO, TITULAR_PRINCIPAL,
    filtros_detalle,
)


_REACTIVACIONES = f"""
    WITH CuentasCandidatas AS (
        SELECT DISTINCT H.NUMEROCUENTA
        FROM AHORROS.CUENTAESTADO_HISTORICO AS H
        INNER JOIN AHORROS.CUENTA AS C ON C.NUMERO = H.NUMEROCUENTA
        {{fuente_cargo}}
        WHERE C.IDAGENCIA IN :ids_agencia
          AND H.CODIGOESTADOCAMBIO = N'I'
          AND H.FECHA >= :fecha_inicio AND H.FECHA < :fecha_hasta_exclusiva
          {{filtros_seleccion}}
    ),
    Cambios AS (
        SELECT H.ID, H.NUMEROCUENTA, H.FECHA,
               H.CODIGOESTADOCAMBIO AS estado_anterior,
               {ESTADO_RESULTANTE} AS estado_resultante,
               ACTUAL.IDAGENCIA, ACTUAL.CODIGOTIPOCUENTA, ACTUAL.CODIGOUSUARIOOFICIAL
        FROM AHORROS.CUENTAESTADO_HISTORICO AS H
        INNER JOIN CuentasCandidatas AS CC ON CC.NUMEROCUENTA = H.NUMEROCUENTA
        INNER JOIN AHORROS.CUENTA AS ACTUAL ON ACTUAL.NUMERO = H.NUMEROCUENTA
    ),
    Reactivaciones AS (
        SELECT ID, NUMEROCUENTA, FECHA, IDAGENCIA, CODIGOTIPOCUENTA, CODIGOUSUARIOOFICIAL
        FROM Cambios
        WHERE estado_anterior = N'I' AND estado_resultante = N'A'
          AND FECHA >= :fecha_inicio AND FECHA < :fecha_hasta_exclusiva
    )
"""

_AGRUPADOS = _REACTIVACIONES.format(fuente_cargo="", filtros_seleccion="") + """
    , Agrupados AS (
        SELECT R.IDAGENCIA, R.CODIGOTIPOCUENTA, R.CODIGOUSUARIOOFICIAL,
               COUNT_BIG(DISTINCT R.NUMEROCUENTA) AS cantidad_cuentas,
               COUNT_BIG(*) AS cantidad_reactivaciones
        FROM Reactivaciones AS R
        GROUP BY R.IDAGENCIA, R.CODIGOTIPOCUENTA, R.CODIGOUSUARIOOFICIAL
    )
"""

_RESUMEN = _AGRUPADOS + f"""
    SELECT X.IDAGENCIA AS id_agencia, A.NOMBRE AS agencia,
           X.CODIGOTIPOCUENTA AS codigo_tipo_cuenta, TC.NOMBRE AS tipo_cuenta,
           X.CODIGOUSUARIOOFICIAL AS codigo_asesor, U.NOMBRE AS asesor,
           {NOMBRE_CARGO} AS cargo, X.cantidad_cuentas, X.cantidad_reactivaciones
    FROM Agrupados AS X
    INNER JOIN GENERAL.AGENCIA AS A ON A.ID = X.IDAGENCIA
    INNER JOIN AHORROS.TIPO_CUENTA AS TC ON TC.CODIGO = X.CODIGOTIPOCUENTA
    INNER JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = X.CODIGOUSUARIOOFICIAL
    {CARGO_OFICIAL.format(usuario="X.CODIGOUSUARIOOFICIAL")}
    ORDER BY A.NOMBRE, X.IDAGENCIA, TC.NOMBRE, X.CODIGOTIPOCUENTA, U.NOMBRE, X.CODIGOUSUARIOOFICIAL
"""

_DETALLE = _REACTIVACIONES + f"""
    , EventosPaginados AS (
        SELECT R.ID, R.NUMEROCUENTA AS NUMERO, R.FECHA, R.IDAGENCIA, R.CODIGOTIPOCUENTA,
               R.CODIGOUSUARIOOFICIAL
        FROM Reactivaciones AS R
        ORDER BY R.FECHA DESC, R.ID DESC
        OFFSET :desplazamiento ROWS FETCH NEXT :tamano_pagina ROWS ONLY
    )
    SELECT C.ID AS id_reactivacion, C.NUMERO AS numero_cuenta,
           CAST(C.FECHA AS date) AS fecha_reactivacion, T.titular,
           TC.NOMBRE AS tipo_cuenta, A.NOMBRE AS agencia,
           U.NOMBRE AS asesor, {NOMBRE_CARGO} AS cargo
    FROM EventosPaginados AS C
    INNER JOIN GENERAL.AGENCIA AS A ON A.ID = C.IDAGENCIA
    INNER JOIN AHORROS.TIPO_CUENTA AS TC ON TC.CODIGO = C.CODIGOTIPOCUENTA
    INNER JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = C.CODIGOUSUARIOOFICIAL
    {CARGO_OFICIAL.format(usuario="C.CODIGOUSUARIOOFICIAL")}
    {TITULAR_PRINCIPAL}
    ORDER BY C.FECHA DESC, C.ID DESC
"""


class SqlControlCuentasActivasRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_resumen(
        self, ids_agencia: list[int], fecha_inicio: date, fecha_fin: date,
    ) -> list[RowMapping]:
        consulta = text(_RESUMEN).bindparams(AGENCIA_EXPANDIBLE)
        return list(self.db.execute(
            consulta, self._parametros(ids_agencia, fecha_inicio, fecha_fin),
        ).mappings().all())

    def obtener_detalle(
        self, ids_agencia: list[int], fecha_inicio: date, fecha_fin: date, *,
        cargos: list[str], asesores: list[str], desplazamiento: int, tamano_pagina: int,
        codigo_tipo_cuenta: str | None = None,
    ) -> list[RowMapping]:
        params = self._parametros(ids_agencia, fecha_inicio, fecha_fin)
        params.update(desplazamiento=desplazamiento, tamano_pagina=tamano_pagina)
        fuente_cargo, filtros, expandibles = filtros_detalle(
            params, codigo_oficial=None, codigo_tipo_cuenta=codigo_tipo_cuenta,
            cargos=cargos, asesores=asesores,
        )
        consulta = text(_DETALLE.format(
            fuente_cargo=fuente_cargo, filtros_seleccion=filtros,
        )).bindparams(*expandibles)
        return list(self.db.execute(consulta, params).mappings().all())

    @staticmethod
    def _parametros(
        ids_agencia: list[int], fecha_inicio: date, fecha_fin: date,
    ) -> dict[str, object]:
        return {
            "ids_agencia": ids_agencia,
            "fecha_inicio": fecha_inicio,
            "fecha_hasta_exclusiva": fecha_fin + timedelta(days=1),
        }

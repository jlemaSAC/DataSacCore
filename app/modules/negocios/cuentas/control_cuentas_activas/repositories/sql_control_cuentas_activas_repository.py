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
        SELECT H.ID, H.NUMEROCUENTA, H.FECHA, H.FECHAPROCESO, H.CODIGOUSUARIO,
               H.CODIGOESTADOCAMBIO AS estado_anterior,
               {ESTADO_RESULTANTE} AS estado_resultante,
               ACTUAL.IDAGENCIA, ACTUAL.CODIGOTIPOCUENTA, ACTUAL.CODIGOUSUARIOOFICIAL
        FROM AHORROS.CUENTAESTADO_HISTORICO AS H
        INNER JOIN CuentasCandidatas AS CC ON CC.NUMEROCUENTA = H.NUMEROCUENTA
        INNER JOIN AHORROS.CUENTA AS ACTUAL ON ACTUAL.NUMERO = H.NUMEROCUENTA
    ),
    ReactivacionesOrdenadas AS (
        SELECT ID, NUMEROCUENTA AS NUMERO, FECHA, FECHAPROCESO, CODIGOUSUARIO,
               IDAGENCIA, CODIGOTIPOCUENTA, CODIGOUSUARIOOFICIAL,
               ROW_NUMBER() OVER (
                   PARTITION BY NUMEROCUENTA, CAST(FECHA AS date)
                   ORDER BY FECHAPROCESO DESC, ID DESC
               ) AS orden
        FROM Cambios
        WHERE estado_anterior = N'I' AND estado_resultante = N'A'
          AND FECHA >= :fecha_inicio AND FECHA < :fecha_hasta_exclusiva
    ),
    Reactivaciones AS (
        SELECT *
        FROM ReactivacionesOrdenadas
        WHERE orden = 1
    )
"""

# No existe un ID de movimiento en el histórico. También se exige coincidencia
# de cuenta, usuario, fecha de negocio y estado activo para vincular un movimiento
# registrado hasta diez segundos antes del cambio.
_MOVIMIENTO_REACTIVACION = """
    OUTER APPLY (
        SELECT TOP (1) MT.IDTRANSACCION,
               SUM(CASE WHEN MD.DEBITO = 1 THEN MD.VALOR ELSE 0 END) AS debitos,
               SUM(CASE WHEN MD.DEBITO = 0 THEN MD.VALOR ELSE 0 END) AS creditos
        FROM AHORROS.CUENTA_MOVIMIENTOTRANSACCIONDETALLE AS CM
        INNER JOIN FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE AS MD
            ON MD.ID = CM.IDMOVIMIENTOTRANSACCIONDETALLE
        INNER JOIN FINANCIERO.MOVIMIENTO_TRANSACCION AS MT ON MT.ID = MD.IDMOVIMIENTOTRANSACCION
        WHERE CM.NUMEROCUENTA = C.NUMERO
          AND CM.CODIGOESTADOCUENTA = N'A'
          AND MT.CODIGOUSUARIO = C.CODIGOUSUARIO
          AND MT.FECHASISTEMA >= CAST(C.FECHA AS date)
          AND MT.FECHASISTEMA < DATEADD(day, 1, CAST(C.FECHA AS date))
          AND MT.FECHAPROCESO >= DATEADD(second, -10, C.FECHAPROCESO)
          AND MT.FECHAPROCESO <= C.FECHAPROCESO
        GROUP BY MT.ID, MT.IDTRANSACCION, MT.FECHAPROCESO
        ORDER BY MT.FECHAPROCESO DESC, MT.ID DESC
    ) AS Mov
"""

# Un traspaso interno puede registrar el mismo importe en ambos lados.
_VALOR_REACTIVACION = "CASE WHEN Mov.debitos > Mov.creditos THEN Mov.debitos ELSE Mov.creditos END"

_AGRUPADOS = _REACTIVACIONES.format(fuente_cargo="", filtros_seleccion="") + f"""
    , Agrupados AS (
        SELECT C.IDAGENCIA, C.CODIGOTIPOCUENTA, C.CODIGOUSUARIOOFICIAL,
               COUNT_BIG(DISTINCT C.NUMERO) AS cantidad_cuentas,
               COUNT_BIG(*) AS cantidad_reactivaciones,
               SUM({_VALOR_REACTIVACION}) AS total_recaudado
        FROM Reactivaciones AS C
        {_MOVIMIENTO_REACTIVACION}
        GROUP BY C.IDAGENCIA, C.CODIGOTIPOCUENTA, C.CODIGOUSUARIOOFICIAL
    )
"""

_RESUMEN = _AGRUPADOS + f"""
    SELECT X.IDAGENCIA AS id_agencia, A.NOMBRE AS agencia,
           X.CODIGOTIPOCUENTA AS codigo_tipo_cuenta, TC.NOMBRE AS tipo_cuenta,
           X.CODIGOUSUARIOOFICIAL AS codigo_asesor, U.NOMBRE AS asesor,
           {NOMBRE_CARGO} AS cargo, X.cantidad_cuentas, X.cantidad_reactivaciones,
           X.total_recaudado
    FROM Agrupados AS X
    INNER JOIN GENERAL.AGENCIA AS A ON A.ID = X.IDAGENCIA
    INNER JOIN AHORROS.TIPO_CUENTA AS TC ON TC.CODIGO = X.CODIGOTIPOCUENTA
    INNER JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = X.CODIGOUSUARIOOFICIAL
    {CARGO_OFICIAL.format(usuario="X.CODIGOUSUARIOOFICIAL")}
"""

_PAGINACION = """
    ORDER BY R.FECHA DESC, R.FECHAPROCESO DESC, R.ID DESC
    OFFSET :desplazamiento ROWS FETCH NEXT :tamano_pagina ROWS ONLY
"""

_DETALLE = _REACTIVACIONES + f"""
    , EventosSeleccionados AS (
        SELECT R.ID, R.NUMERO, R.FECHA, R.FECHAPROCESO, R.CODIGOUSUARIO,
               R.IDAGENCIA, R.CODIGOTIPOCUENTA, R.CODIGOUSUARIOOFICIAL
        FROM Reactivaciones AS R
        {{paginacion}}
    )
    SELECT C.ID AS id_reactivacion, C.NUMERO AS numero_cuenta,
           CAST(C.FECHA AS date) AS fecha_reactivacion, T.titular,
           TC.NOMBRE AS tipo_cuenta, A.NOMBRE AS agencia,
           U.NOMBRE AS asesor, {NOMBRE_CARGO} AS cargo, TR.NOMBRE AS transaccion,
           {_VALOR_REACTIVACION} AS valor_transaccion
    FROM EventosSeleccionados AS C
    INNER JOIN GENERAL.AGENCIA AS A ON A.ID = C.IDAGENCIA
    INNER JOIN AHORROS.TIPO_CUENTA AS TC ON TC.CODIGO = C.CODIGOTIPOCUENTA
    INNER JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = C.CODIGOUSUARIOOFICIAL
    {CARGO_OFICIAL.format(usuario="C.CODIGOUSUARIOOFICIAL")}
    {TITULAR_PRINCIPAL}
    {_MOVIMIENTO_REACTIVACION}
    LEFT JOIN FINANCIERO.TRANSACCION AS TR ON TR.ID = Mov.IDTRANSACCION
    ORDER BY C.FECHA DESC, C.FECHAPROCESO DESC, C.ID DESC
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
        sin_paginacion: bool = False,
    ) -> list[RowMapping]:
        params = self._parametros(ids_agencia, fecha_inicio, fecha_fin)
        if not sin_paginacion:
            params.update(desplazamiento=desplazamiento, tamano_pagina=tamano_pagina)
        fuente_cargo, filtros, expandibles = filtros_detalle(
            params, codigo_oficial=None, codigo_tipo_cuenta=codigo_tipo_cuenta,
            cargos=cargos, asesores=asesores,
        )
        consulta = text(_DETALLE.format(
            fuente_cargo=fuente_cargo, filtros_seleccion=filtros,
            paginacion="" if sin_paginacion else _PAGINACION,
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

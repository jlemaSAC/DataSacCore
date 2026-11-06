from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
import random
import re
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


class DeadlockDiarioError(RuntimeError):
    """La lectura no pudo completarse tras los reintentos por deadlock."""


def _es_deadlock(error: DBAPIError) -> bool:
    # SQLSTATE 40001 también se usa para otros conflictos de transacción.
    # Revisar el código nativo del driver, sin inspeccionar SQL ni parámetros.
    return any(
        argumento == 1205 or re.search(r"\(1205\)(?:\s|$)", str(argumento))
        for argumento in error.orig.args
    )


@dataclass(frozen=True)
class CorteDepositosYRetiros:
    fecha: date
    filas: list[dict[str, Any]]


@dataclass(frozen=True)
class _Corte:
    fecha: date
    cierre: datetime | None
    en_linea: bool


class SqlDepositosYRetirosDiariosRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _obtener_corte(self, fecha_fin: date, fecha_sistema: date) -> _Corte | None:
        corte = self.db.execute(text("""
            SELECT TOP (1) CAST(CS.FECHASISTEMA AS date) AS fecha,
                CS.SECERRO AS cerrado, C.FECHACIERREVISTA AS cierre
            FROM GENERAL.CALENDARIO_SISTEMA AS CS
            LEFT JOIN GENERAL.EMPRESA_CIERREHISTORICO AS C
                ON C.FECHASISTEMA = CS.FECHASISTEMA
            WHERE CS.FECHASISTEMA >= :inicio_mes
              AND CS.FECHASISTEMA < :hasta_exclusivo
            ORDER BY CS.FECHASISTEMA DESC
        """), {
            "inicio_mes": fecha_fin.replace(day=1),
            "hasta_exclusivo": fecha_fin + timedelta(days=1),
        }).mappings().first()
        if corte is None:
            return None
        fecha = corte["fecha"]
        if isinstance(fecha, datetime):
            fecha = fecha.date()
        en_linea = fecha == fecha_sistema and not corte["cerrado"]
        if not en_linea and corte["cierre"] is None:
            return None
        return _Corte(fecha, corte["cierre"], en_linea)

    def obtener_diario(
        self, *, fecha_inicio: date, fecha_fin: date, fecha_sistema: date, id_agencia: int,
    ) -> CorteDepositosYRetiros | None:
        for intento in range(3):
            try:
                return self._consultar_diario(
                    fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
                    fecha_sistema=fecha_sistema, id_agencia=id_agencia,
                )
            except DBAPIError as error:
                if not _es_deadlock(error):
                    raise
                # Este repositorio solo lee. Reiniciar tanto el corte como los
                # movimientos; nunca reutilizar una transacción cancelada.
                self.db.rollback()
                if intento == 2:
                    logger.warning("Deadlock en el reporte diario de Ahorro Vista: agotados 3 intentos.")
                    raise DeadlockDiarioError() from error
                logger.warning("Deadlock en el reporte diario de Ahorro Vista; reintento %s de 2.", intento + 1)
                time.sleep(random.uniform(0.2, 0.5) * (2 ** intento))

    def _consultar_diario(
        self, *, fecha_inicio: date, fecha_fin: date, fecha_sistema: date, id_agencia: int,
    ) -> CorteDepositosYRetiros | None:
        corte = self._obtener_corte(fecha_fin, fecha_sistema)
        if corte is None:
            return None
        temporal = "" if corte.en_linea else "FOR SYSTEM_TIME AS OF :cierre"
        filtro_agencia = "AND CU.IDAGENCIA = :id_agencia" if id_agencia else ""
        # Compensar detalles solo dentro de la misma operación y cuenta. Así los
        # movimientos internos no inflan entradas/salidas y dos operaciones reales
        # del mismo día no se cancelan entre sí.
        # No se leen saldos, tasas, ítems ni clientes y no se crean tablas temporales.
        statement = text(f"""
            WITH MovimientosNetos AS (
                SELECT MT.ID AS id_movimiento, MT.IDTRANSACCION AS id_transaccion, CM.NUMEROCUENTA,
                    CAST(MT.FECHASISTEMA AS date) AS fecha,
                    SUM(CASE WHEN MD.DEBITO = 0 THEN MD.VALOR ELSE -MD.VALOR END) AS variacion
                FROM FINANCIERO.MOVIMIENTO_TRANSACCION AS MT
                INNER JOIN FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE AS MD
                    ON MD.IDMOVIMIENTOTRANSACCION = MT.ID
                INNER JOIN AHORROS.CUENTA_MOVIMIENTOTRANSACCIONDETALLE AS CM
                    ON CM.IDMOVIMIENTOTRANSACCIONDETALLE = MD.ID
                WHERE MT.FECHASISTEMA >= :fecha_inicio
                  AND MT.FECHASISTEMA < :hasta_exclusivo
                  AND NOT EXISTS (
                    SELECT 1 FROM FINANCIERO.MOVIMIENTO_TRANSACCION_REVERSO AS R
                    INNER JOIN FINANCIERO.MOVIMIENTO_TRANSACCION AS MR
                        ON MR.ID = R.IDMOVIMIENTOREVERSO
                    WHERE R.IDMOVIMIENTO = MT.ID
                      AND MR.FECHASISTEMA < :hasta_exclusivo
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM FINANCIERO.MOVIMIENTO_TRANSACCION_REVERSO AS R
                    WHERE R.IDMOVIMIENTOREVERSO = MT.ID
                  )
                GROUP BY MT.ID, MT.IDTRANSACCION, CM.NUMEROCUENTA, CAST(MT.FECHASISTEMA AS date)
                HAVING SUM(CASE WHEN MD.DEBITO = 0 THEN MD.VALOR ELSE -MD.VALOR END) <> 0
            ), MovimientosPorCuenta AS (
                SELECT NUMEROCUENTA, fecha, id_transaccion,
                    SUM(CASE WHEN variacion > 0 THEN variacion ELSE 0 END) AS depositos,
                    SUM(CASE WHEN variacion < 0 THEN -variacion ELSE 0 END) AS retiros
                FROM MovimientosNetos
                GROUP BY NUMEROCUENTA, fecha, id_transaccion
            ), Agrupados AS (
                SELECT CU.IDAGENCIA AS id_agencia,
                    COALESCE(NULLIF(LTRIM(RTRIM(CU.CODIGOUSUARIOOFICIAL)), N''), N'SIN USUARIO') AS codigo_usuario,
                    CU.CODIGOTIPOCUENTA AS codigo_producto, M.fecha, M.id_transaccion,
                    SUM(M.depositos) AS depositos, SUM(M.retiros) AS retiros
                FROM MovimientosPorCuenta AS M
                INNER JOIN AHORROS.CUENTA {temporal} AS CU ON CU.NUMERO = M.NUMEROCUENTA
                INNER JOIN AHORROS.TIPO_CUENTA AS TC
                    ON TC.CODIGO = CU.CODIGOTIPOCUENTA AND TC.ESPROGRAMADO = 0
                WHERE CU.CODIGOTIPOCUENTA <> N'001'
                  {filtro_agencia}
                GROUP BY CU.IDAGENCIA,
                    COALESCE(NULLIF(LTRIM(RTRIM(CU.CODIGOUSUARIOOFICIAL)), N''), N'SIN USUARIO'),
                    CU.CODIGOTIPOCUENTA, M.fecha, M.id_transaccion
            )
            SELECT X.*,
                COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), N''), N'SIN AGENCIA') AS agencia,
                COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), N''), X.codigo_usuario) AS nombre_asesor,
                COALESCE(NULLIF(LTRIM(RTRIM(TC.NOMBRE)), N''), X.codigo_producto) AS producto_ahorro,
                COALESCE(NULLIF(LTRIM(RTRIM(T.NOMBRE)), N''), CAST(X.id_transaccion AS nvarchar(20))) AS tipo_transaccion
            FROM Agrupados AS X
            LEFT JOIN GENERAL.AGENCIA AS A ON A.ID = X.id_agencia
            LEFT JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = X.codigo_usuario
            INNER JOIN AHORROS.TIPO_CUENTA AS TC ON TC.CODIGO = X.codigo_producto
            LEFT JOIN FINANCIERO.TRANSACCION AS T ON T.ID = X.id_transaccion
        """)
        filas = self.db.execute(statement, {
            "fecha_inicio": fecha_inicio,
            "hasta_exclusivo": corte.fecha + timedelta(days=1),
            "id_agencia": id_agencia, "cierre": corte.cierre,
        }).mappings().all()
        return CorteDepositosYRetiros(corte.fecha, [dict(fila) for fila in filas])

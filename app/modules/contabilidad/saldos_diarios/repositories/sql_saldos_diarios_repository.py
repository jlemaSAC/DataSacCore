from datetime import date
from typing import Any, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session


class SqlSaldosDiariosRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_empresa_agencia(self, id_agencia: int) -> int | None:
        return self.db.execute(
            text("SELECT IDEMPRESA FROM GENERAL.AGENCIA WHERE ID = :id_agencia"),
            {"id_agencia": id_agencia},
        ).scalar_one_or_none()

    def obtener_cuentas_activas(self, id_empresa: int) -> list[dict[str, Any]]:
        rows = self.db.execute(
            text("""
                SELECT CODIGO AS codigo_cuenta, NOMBRE AS nombre_cuenta
                FROM CONTABILIDAD.CUENTACONTABLE
                WHERE IDEMPRESA = :id_empresa AND ACTIVA = 1
                ORDER BY CODIGO
            """),
            {"id_empresa": id_empresa},
        ).mappings()
        return [dict(row) for row in rows]

    def obtener_saldos(self, *, fecha_desde: date, fecha_hasta: date,
                       id_agencia: int, fechas: Sequence[date] | None = None,
                       id_empresa: int | None = None) -> list[dict[str, Any]]:
        if fechas is not None and not fechas:
            return []
        parametros: dict[str, Any] = {
            "fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta, "id_agencia": id_agencia,
        }
        join_fechas = ""
        if fechas is not None:
            # Predicados sobre FECHA sin CAST para aprovechar los índices agencia/fecha.
            cortes = list(dict.fromkeys(fechas))
            valores = ", ".join(f"(CAST(:corte_{i} AS date))" for i in range(len(cortes)))
            parametros.update({f"corte_{i}": fecha for i, fecha in enumerate(cortes)})
            join_fechas = f"""INNER JOIN (VALUES {valores}) cortes(fecha)
                ON sc.FECHA >= cortes.fecha AND sc.FECHA < DATEADD(day, 1, cortes.fecha)"""
        filtro_empresa = "AND c.IDEMPRESA = :id_empresa" if id_empresa is not None else ""
        if id_empresa is not None:
            parametros["id_empresa"] = id_empresa
        # Se incluyen también las cuentas inactivas que pueden intervenir en el neteo.
        rows = self.db.execute(
            text(f"""
                SELECT CAST(sc.FECHA AS date) AS fecha, sc.CODIGOCUENTA AS codigo_cuenta,
                       SUM(CASE WHEN LEFT(c.CODIGO, 1) NOT IN ('6', '7') AND c.ESDEBITO = 0
                                THEN -1 ELSE 1 END *
                           (COALESCE(sf.SALDOINICIAL, sc.SALDOINICIAL)
                            + COALESCE(sf.TOTALDEBITO, sc.TOTALDEBITO)
                            - COALESCE(sf.TOTALCREDITO, sc.TOTALCREDITO))) AS saldo
                FROM CONTABILIDAD.SALDOCONTABLE sc
                {join_fechas}
                INNER JOIN CONTABILIDAD.CUENTACONTABLE c ON c.CODIGO = sc.CODIGOCUENTA
                LEFT JOIN CONTABILIDAD.SALDOCONTABLE_FINANIO sf
                  ON sf.CODIGOCUENTA = sc.CODIGOCUENTA AND sf.FECHA = sc.FECHA
                 AND sf.IDAGENCIA = sc.IDAGENCIA AND sf.IDMONEDA = sc.IDMONEDA
                WHERE sc.IDAGENCIA = :id_agencia
                  {filtro_empresa}
                  AND sc.FECHA >= :fecha_desde AND sc.FECHA < DATEADD(day, 1, :fecha_hasta)
                GROUP BY CAST(sc.FECHA AS date), sc.CODIGOCUENTA
            """),
            parametros,
        ).mappings()
        return [dict(row) for row in rows]

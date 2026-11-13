from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


class SqlResumenContableRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_agencia(self, id_agencia: int) -> dict | None:
        row = self.db.execute(
            text("SELECT NOMBRE AS nombre, IDEMPRESA AS id_empresa FROM GENERAL.AGENCIA WHERE ID = :id_agencia"),
            {"id_agencia": id_agencia},
        ).mappings().one_or_none()
        return dict(row) if row is not None else None

    def obtener_saldos(self, *, fecha_corte: date, id_agencia: int,
                       id_empresa: int, codigos_cuenta: Sequence[str]) -> dict[str, Decimal]:
        rows = self.obtener_saldos_fechas(
            fechas=[fecha_corte], id_agencia=id_agencia,
            id_empresa=id_empresa, codigos_cuenta=codigos_cuenta,
        )
        return {row["codigo_cuenta"]: row["saldo"] for row in rows}

    def obtener_saldos_fechas(self, *, fechas: Sequence[date], id_agencia: int,
                              id_empresa: int, codigos_cuenta: Sequence[str]) -> list[dict]:
        if not codigos_cuenta or not fechas:
            return []
        # Misma regla de signo y cierre anual que SALDOCONTABLEREPORTE.
        # Leer tablas conserva ceros; consultar códigos exactos evita sumar padres e hijos.
        stmt = text("""
            SELECT CAST(sc.FECHA AS date) AS fecha, sc.CODIGOCUENTA AS codigo_cuenta,
                   SUM(CASE WHEN c.ESDEBITO = 0 THEN -1 ELSE 1 END *
                       (COALESCE(sf.SALDOINICIAL, sc.SALDOINICIAL)
                        + COALESCE(sf.TOTALDEBITO, sc.TOTALDEBITO)
                        - COALESCE(sf.TOTALCREDITO, sc.TOTALCREDITO))) AS saldo
            FROM CONTABILIDAD.SALDOCONTABLE sc
            INNER JOIN CONTABILIDAD.CUENTACONTABLE c ON c.CODIGO = sc.CODIGOCUENTA
            LEFT JOIN CONTABILIDAD.SALDOCONTABLE_FINANIO sf
              ON sf.CODIGOCUENTA = sc.CODIGOCUENTA AND sf.FECHA = sc.FECHA
             AND sf.IDAGENCIA = sc.IDAGENCIA AND sf.IDMONEDA = sc.IDMONEDA
            WHERE sc.IDAGENCIA = :id_agencia AND c.IDEMPRESA = :id_empresa
              AND sc.FECHA >= :fecha_desde AND sc.FECHA < DATEADD(day, 1, :fecha_hasta)
              AND CAST(sc.FECHA AS date) IN :fechas
              AND sc.CODIGOCUENTA IN :codigos_cuenta
            GROUP BY CAST(sc.FECHA AS date), sc.CODIGOCUENTA
        """).bindparams(bindparam("codigos_cuenta", expanding=True), bindparam("fechas", expanding=True))
        rows = self.db.execute(stmt, {
            "fecha_desde": min(fechas), "fecha_hasta": max(fechas),
            "fechas": list(dict.fromkeys(fechas)), "id_agencia": id_agencia,
            "id_empresa": id_empresa, "codigos_cuenta": list(codigos_cuenta),
        }).mappings()
        return [dict(row) for row in rows]

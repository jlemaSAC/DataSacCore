from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


class SqlCuentasContablesRepository:
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
        if not codigos_cuenta:
            return {}
        # Misma regla de signo y cierre anual que SALDOCONTABLEREPORTE.
        # Leer tablas conserva ceros; consultar códigos exactos evita sumar padres e hijos.
        stmt = text("""
            SELECT sc.CODIGOCUENTA AS codigo_cuenta,
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
              AND sc.FECHA >= :fecha_corte AND sc.FECHA < DATEADD(day, 1, :fecha_corte)
              AND sc.CODIGOCUENTA IN :codigos_cuenta
            GROUP BY sc.CODIGOCUENTA
        """).bindparams(bindparam("codigos_cuenta", expanding=True))
        rows = self.db.execute(stmt, {
            "fecha_corte": fecha_corte, "id_agencia": id_agencia,
            "id_empresa": id_empresa, "codigos_cuenta": list(codigos_cuenta),
        }).mappings()
        return {row["codigo_cuenta"]: row["saldo"] for row in rows}

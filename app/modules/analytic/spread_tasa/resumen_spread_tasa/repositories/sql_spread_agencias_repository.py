from datetime import datetime
from typing import Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


class SqlSpreadAgenciasRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_saldos(self, *, fechas: Sequence[datetime], ids_agencia: Sequence[int],
                        codigos_cuenta: Sequence[str]) -> list[dict]:
        if not fechas or not ids_agencia or not codigos_cuenta:
            return []
        # Reproduce la vista neteada y el ajuste de la cuenta 41 utilizado por
        # SqlSaldoContableRepository, agrupando por agencia antes de calcular.
        stmt = text("""
            WITH SaldosBase AS (
                SELECT r.IDAGENCIA, r.FECHA, r.CODIGOCUENTA, SUM(r.SALDO) AS SaldoOriginal
                FROM CONTABILIDAD.SALDOCONTABLEREPORTE_NETEO r
                WHERE r.IDAGENCIA IN :ids_agencia AND r.FECHA IN :fechas
                  AND r.CODIGOCUENTA IN :codigos_cuenta
                GROUP BY r.IDAGENCIA, r.FECHA, r.CODIGOCUENTA
            ), Neteo41 AS (
                SELECT r.IDAGENCIA, r.FECHA, r.CODIGOCUENTA, SUM(r.SALDO) AS saldo
                FROM CONTABILIDAD.SALDOCONTABLEREPORTE r
                WHERE r.IDAGENCIA IN :ids_agencia AND r.FECHA IN :fechas
                  AND r.CODIGOCUENTA IN ('41', '41019005')
                GROUP BY r.IDAGENCIA, r.FECHA, r.CODIGOCUENTA
            )
            SELECT s.IDAGENCIA AS IdAgencia, s.FECHA AS Fecha, s.CODIGOCUENTA AS CodigoCuenta,
                   CASE WHEN s.CODIGOCUENTA = '41' THEN COALESCE(t.saldo, 0) - COALESCE(n.saldo, 0)
                        ELSE s.SaldoOriginal END AS SaldoFinal
            FROM SaldosBase s
            LEFT JOIN Neteo41 t ON t.IDAGENCIA = s.IDAGENCIA AND t.FECHA = s.FECHA AND t.CODIGOCUENTA = '41'
            LEFT JOIN Neteo41 n ON n.IDAGENCIA = s.IDAGENCIA AND n.FECHA = s.FECHA AND n.CODIGOCUENTA = '41019005'
        """).bindparams(bindparam('ids_agencia', expanding=True), bindparam('fechas', expanding=True),
                        bindparam('codigos_cuenta', expanding=True))
        rows = self.db.execute(stmt, {'ids_agencia': list(ids_agencia), 'fechas': list(fechas),
                                      'codigos_cuenta': list(codigos_cuenta)}).mappings().all()
        return [dict(row) for row in rows]

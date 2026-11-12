from datetime import date
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.contabilidad.saldos_diarios.repositories.sql_saldos_diarios_repository import SqlSaldosDiariosRepository


class SqlComparativaCuentasRepository:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.saldos = SqlSaldosDiariosRepository(db)

    def obtener_agencia(self, id_agencia: int) -> dict | None:
        row = self.db.execute(text("""
            SELECT NOMBRE AS nombre, IDEMPRESA AS id_empresa
            FROM GENERAL.AGENCIA WHERE ID = :id_agencia
        """), {"id_agencia": id_agencia}).mappings().one_or_none()
        return dict(row) if row is not None else None

    def obtener_cuentas(self, id_empresa: int) -> list[dict]:
        rows = self.db.execute(text("""
            SELECT c.CODIGO AS codigo_cuenta, c.NOMBRE AS nombre_cuenta,
                   c.ACTIVA AS activa, c.ESDEMOVIMIENTO AS es_movimiento,
                   padre.CODIGOCUENTAPADRE AS codigo_padre
            FROM CONTABILIDAD.CUENTACONTABLE c
            OUTER APPLY (
                SELECT TOP (1) p.CODIGOCUENTAPADRE
                FROM CONTABILIDAD.CUENTACONTABLE_PADRE p
                INNER JOIN CONTABILIDAD.CUENTACONTABLE cp ON cp.CODIGO = p.CODIGOCUENTAPADRE
                WHERE p.CODIGOCUENTA = c.CODIGO AND cp.IDEMPRESA = :id_empresa
                  AND p.CODIGOCUENTAPADRE <> c.CODIGO
                ORDER BY LEN(p.CODIGOCUENTAPADRE) DESC, p.CODIGOCUENTAPADRE
            ) padre
            WHERE c.IDEMPRESA = :id_empresa
            ORDER BY c.CODIGO
        """), {"id_empresa": id_empresa}).mappings()
        return [dict(row) for row in rows]

    def obtener_saldos(self, *, fechas: Sequence[date], id_agencia: int, id_empresa: int, rango_continuo: bool = False) -> list[dict]:
        if not fechas:
            return []
        if rango_continuo:
            return self.saldos.obtener_saldos(
                fecha_desde=min(fechas), fecha_hasta=max(fechas), id_agencia=id_agencia,
                id_empresa=id_empresa,
            )
        # SQL Server limita a 1000 filas el constructor VALUES usado para los cortes.
        resultado = []
        for inicio in range(0, len(fechas), 1000):
            lote = fechas[inicio:inicio + 1000]
            resultado.extend(self.saldos.obtener_saldos(
                fecha_desde=min(lote), fecha_hasta=max(lote), id_agencia=id_agencia,
                fechas=lote, id_empresa=id_empresa,
            ))
        return resultado

    def obtener_movimientos_mensuales(self, *, fechas: Sequence[date], id_agencia: int, id_empresa: int) -> list[dict]:
        """Movimiento neto del día 1 al corte; un rango incompleto conserva null."""
        cortes = sorted(set(fechas))
        resultado = []
        for inicio in range(0, len(cortes), 500):
            lote = cortes[inicio:inicio + 500]
            valores = ", ".join(f"(CAST(:corte_{i} AS date))" for i in range(len(lote)))
            parametros = {f"corte_{i}": fecha for i, fecha in enumerate(lote)}
            parametros.update(id_agencia=id_agencia, id_empresa=id_empresa)
            rows = self.db.execute(text(f"""
                SELECT cortes.fecha, sc.CODIGOCUENTA AS codigo_cuenta,
                       CASE WHEN COUNT(DISTINCT CAST(sc.FECHA AS date)) = DAY(cortes.fecha)
                            THEN SUM(CASE WHEN LEFT(c.CODIGO, 1) NOT IN ('6', '7') AND c.ESDEBITO = 0
                                          THEN -1 ELSE 1 END *
                                     (COALESCE(sf.TOTALDEBITO, sc.TOTALDEBITO)
                                      - COALESCE(sf.TOTALCREDITO, sc.TOTALCREDITO)))
                            ELSE NULL END AS saldo
                FROM (VALUES {valores}) cortes(fecha)
                INNER JOIN CONTABILIDAD.SALDOCONTABLE sc
                  ON sc.FECHA >= DATEFROMPARTS(YEAR(cortes.fecha), MONTH(cortes.fecha), 1)
                 AND sc.FECHA < DATEADD(day, 1, cortes.fecha)
                INNER JOIN CONTABILIDAD.CUENTACONTABLE c ON c.CODIGO = sc.CODIGOCUENTA
                LEFT JOIN CONTABILIDAD.SALDOCONTABLE_FINANIO sf
                  ON sf.CODIGOCUENTA = sc.CODIGOCUENTA AND sf.FECHA = sc.FECHA
                 AND sf.IDAGENCIA = sc.IDAGENCIA AND sf.IDMONEDA = sc.IDMONEDA
                WHERE sc.IDAGENCIA = :id_agencia AND c.IDEMPRESA = :id_empresa
                GROUP BY cortes.fecha, sc.CODIGOCUENTA
            """), parametros).mappings()
            resultado.extend(dict(row) for row in rows)
        return resultado

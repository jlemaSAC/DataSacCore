from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable, Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


MAPA_NETEO_CUENTAS: dict[str, str] = {
    "1": "1908",
    "19": "1908",
    "2": "2908",
    "29": "2908",
    "4": "41019005",
    "41": "41019005",
    "4101": "41019005",
    "410190": "41019005",
    "5": "51909005",
    "51": "51909005",
    "5190": "51909005",
    "519090": "51909005",
}


class SqlSaldoContableRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_saldos_contables_con_neteo(
        self,
        *,
        fecha: datetime,
        id_agencia: int,
        codigos_cuenta: Sequence[str],
        neteo: int | bool = 1,
    ) -> list[dict[str, Any]]:
        codigos_normalizados = normalizar_codigos_cuenta(codigos_cuenta)
        if not codigos_normalizados:
            return []

        tabla_base = (
            "CONTABILIDAD.SALDOCONTABLEREPORTE_NETEO"
            if int(bool(neteo))
            else "CONTABILIDAD.SALDOCONTABLEREPORTE"
        )

        stmt = text(
            f"""
            WITH MapaNeteo AS (
                {_mapa_neteo_sql()}
            ),
            SaldosBase AS (
                SELECT
                    r.CODIGOCUENTA,
                    MAX(r.NOMBRECUENTA) AS NOMBRECUENTA,
                    SUM(r.SALDO) AS SaldoOriginal
                FROM {tabla_base} r
                WHERE r.FECHA = :fecha
                  AND r.IDAGENCIA = :id_agencia
                  AND r.CODIGOCUENTA IN :codigos_cuenta
                GROUP BY r.CODIGOCUENTA
            ),
            SaldosFuncionNeteo AS (
                SELECT
                    r.CODIGOCUENTA,
                    SUM(r.SALDO) AS SaldoOriginal
                FROM CONTABILIDAD.SALDOCONTABLEREPORTE r
                WHERE r.FECHA = :fecha
                  AND r.IDAGENCIA = :id_agencia
                  AND r.CODIGOCUENTA IN (
                      SELECT CuentaTotal FROM MapaNeteo
                      UNION
                      SELECT CuentaNeteada FROM MapaNeteo
                  )
                GROUP BY r.CODIGOCUENTA
            )
            SELECT
                s.CODIGOCUENTA AS CodigoCuenta,
                s.NOMBRECUENTA AS NombreCuenta,
                s.SaldoOriginal,
                m.CuentaNeteada,
                sn.SaldoOriginal AS SaldoCuentaNeteada,
                CASE
                    WHEN :neteo = 1 AND m.CuentaNeteada IS NOT NULL THEN
                        COALESCE(st.SaldoOriginal, 0) - COALESCE(sn.SaldoOriginal, 0)
                    ELSE
                        COALESCE(s.SaldoOriginal, 0)
                END AS SaldoFinal
            FROM SaldosBase s
            LEFT JOIN MapaNeteo m
                ON m.CuentaTotal = s.CODIGOCUENTA
            LEFT JOIN SaldosFuncionNeteo st
                ON st.CODIGOCUENTA = s.CODIGOCUENTA
            LEFT JOIN SaldosFuncionNeteo sn
                ON sn.CODIGOCUENTA = m.CuentaNeteada
            ORDER BY s.CODIGOCUENTA
            """
        ).bindparams(bindparam("codigos_cuenta", expanding=True))

        rows = self.db.execute(
            stmt,
            {
                "fecha": fecha,
                "id_agencia": id_agencia,
                "codigos_cuenta": codigos_normalizados,
                "neteo": int(bool(neteo)),
            },
        ).mappings().all()

        return [
            {
                "CodigoCuenta": row.get("CodigoCuenta"),
                "NombreCuenta": row.get("NombreCuenta"),
                "SaldoOriginal": to_float(row.get("SaldoOriginal")),
                "CuentaNeteada": row.get("CuentaNeteada"),
                "SaldoCuentaNeteada": to_float(row.get("SaldoCuentaNeteada")),
                "SaldoFinal": to_float(row.get("SaldoFinal")),
            }
            for row in rows
        ]

    def get_saldo_contable_con_neteo(
        self,
        *,
        fecha: datetime,
        id_agencia: int,
        codigo_cuenta: str,
        neteo: int | bool = 1,
    ) -> float:
        saldos = self.get_saldos_contables_con_neteo(
            fecha=fecha,
            id_agencia=id_agencia,
            codigos_cuenta=[codigo_cuenta],
            neteo=neteo,
        )
        if not saldos:
            return 0.0
        return to_float(saldos[0].get("SaldoFinal"))

    def get_saldos_contables_fechas_con_neteo(
        self,
        *,
        fechas: Sequence[datetime],
        id_agencia: int,
        codigos_cuenta: Sequence[str],
        neteo: int | bool = 1,
    ) -> list[dict[str, Any]]:
        codigos_normalizados = normalizar_codigos_cuenta(codigos_cuenta)
        fechas_normalizadas = list(dict.fromkeys(fechas))
        if not codigos_normalizados or not fechas_normalizadas:
            return []

        tabla_base = (
            "CONTABILIDAD.SALDOCONTABLEREPORTE_NETEO"
            if int(bool(neteo))
            else "CONTABILIDAD.SALDOCONTABLEREPORTE"
        )

        stmt = text(
            f"""
            WITH MapaNeteo AS (
                {_mapa_neteo_sql()}
            ),
            SaldosBase AS (
                SELECT
                    r.FECHA,
                    r.CODIGOCUENTA,
                    SUM(r.SALDO) AS SaldoOriginal
                FROM {tabla_base} r
                WHERE r.FECHA IN :fechas
                  AND r.IDAGENCIA = :id_agencia
                  AND r.CODIGOCUENTA IN :codigos_cuenta
                GROUP BY r.FECHA, r.CODIGOCUENTA
            ),
            SaldosFuncionNeteo AS (
                SELECT
                    r.FECHA,
                    r.CODIGOCUENTA,
                    SUM(r.SALDO) AS SaldoOriginal
                FROM CONTABILIDAD.SALDOCONTABLEREPORTE r
                WHERE r.FECHA IN :fechas
                  AND r.IDAGENCIA = :id_agencia
                  AND r.CODIGOCUENTA IN (
                      SELECT CuentaTotal FROM MapaNeteo
                      UNION
                      SELECT CuentaNeteada FROM MapaNeteo
                  )
                GROUP BY r.FECHA, r.CODIGOCUENTA
            )
            SELECT
                s.FECHA AS Fecha,
                s.CODIGOCUENTA AS CodigoCuenta,
                CASE
                    WHEN :neteo = 1 AND m.CuentaNeteada IS NOT NULL THEN
                        COALESCE(st.SaldoOriginal, 0) - COALESCE(sn.SaldoOriginal, 0)
                    ELSE
                        COALESCE(s.SaldoOriginal, 0)
                END AS SaldoFinal
            FROM SaldosBase s
            LEFT JOIN MapaNeteo m
                ON m.CuentaTotal = s.CODIGOCUENTA
            LEFT JOIN SaldosFuncionNeteo st
                ON st.FECHA = s.FECHA
               AND st.CODIGOCUENTA = s.CODIGOCUENTA
            LEFT JOIN SaldosFuncionNeteo sn
                ON sn.FECHA = s.FECHA
               AND sn.CODIGOCUENTA = m.CuentaNeteada
            ORDER BY s.FECHA, s.CODIGOCUENTA
            """
        ).bindparams(
            bindparam("fechas", expanding=True),
            bindparam("codigos_cuenta", expanding=True),
        )

        rows = self.db.execute(
            stmt,
            {
                "fechas": fechas_normalizadas,
                "id_agencia": id_agencia,
                "codigos_cuenta": codigos_normalizados,
                "neteo": int(bool(neteo)),
            },
        ).mappings().all()

        return [
            {
                "Fecha": row.get("Fecha"),
                "CodigoCuenta": row.get("CodigoCuenta"),
                "SaldoFinal": to_float(row.get("SaldoFinal")),
            }
            for row in rows
        ]

    def get_promedios_saldos_contables_con_neteo(
        self,
        *,
        fecha_desde: datetime,
        fecha_hasta: datetime,
        id_agencia: int,
        codigos_cuenta: Sequence[str],
        neteo: int | bool = 1,
    ) -> list[dict[str, Any]]:
        codigos_normalizados = normalizar_codigos_cuenta(codigos_cuenta)
        if not codigos_normalizados:
            return []

        tabla_base = (
            "CONTABILIDAD.SALDOCONTABLEREPORTE_NETEO"
            if int(bool(neteo))
            else "CONTABILIDAD.SALDOCONTABLEREPORTE"
        )

        stmt = text(
            f"""
            WITH MapaNeteo AS (
                {_mapa_neteo_sql()}
            ),
            SaldosBase AS (
                SELECT
                    r.FECHA,
                    r.CODIGOCUENTA,
                    SUM(r.SALDO) AS SaldoOriginal
                FROM {tabla_base} r
                WHERE r.FECHA BETWEEN :fecha_desde AND :fecha_hasta
                  AND r.IDAGENCIA = :id_agencia
                  AND r.CODIGOCUENTA IN :codigos_cuenta
                GROUP BY r.FECHA, r.CODIGOCUENTA
            ),
            SaldosFuncionNeteo AS (
                SELECT
                    r.FECHA,
                    r.CODIGOCUENTA,
                    SUM(r.SALDO) AS SaldoOriginal
                FROM CONTABILIDAD.SALDOCONTABLEREPORTE r
                WHERE r.FECHA BETWEEN :fecha_desde AND :fecha_hasta
                  AND r.IDAGENCIA = :id_agencia
                  AND r.CODIGOCUENTA IN (
                      SELECT CuentaTotal FROM MapaNeteo
                      UNION
                      SELECT CuentaNeteada FROM MapaNeteo
                  )
                GROUP BY r.FECHA, r.CODIGOCUENTA
            ),
            SaldosFinales AS (
                SELECT
                    s.FECHA,
                    s.CODIGOCUENTA,
                    CASE
                        WHEN :neteo = 1 AND m.CuentaNeteada IS NOT NULL THEN
                            COALESCE(st.SaldoOriginal, 0) - COALESCE(sn.SaldoOriginal, 0)
                        ELSE
                            COALESCE(s.SaldoOriginal, 0)
                    END AS SaldoFinal
                FROM SaldosBase s
                LEFT JOIN MapaNeteo m
                    ON m.CuentaTotal = s.CODIGOCUENTA
                LEFT JOIN SaldosFuncionNeteo st
                    ON st.FECHA = s.FECHA
                   AND st.CODIGOCUENTA = s.CODIGOCUENTA
                LEFT JOIN SaldosFuncionNeteo sn
                    ON sn.FECHA = s.FECHA
                   AND sn.CODIGOCUENTA = m.CuentaNeteada
            )
            SELECT
                CODIGOCUENTA AS CodigoCuenta,
                AVG(SaldoFinal) AS SaldoPromedio
            FROM SaldosFinales
            GROUP BY CODIGOCUENTA
            ORDER BY CODIGOCUENTA
            """
        ).bindparams(bindparam("codigos_cuenta", expanding=True))

        rows = self.db.execute(
            stmt,
            {
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "id_agencia": id_agencia,
                "codigos_cuenta": codigos_normalizados,
                "neteo": int(bool(neteo)),
            },
        ).mappings().all()

        return [
            {
                "CodigoCuenta": row.get("CodigoCuenta"),
                "SaldoPromedio": to_float(row.get("SaldoPromedio")),
            }
            for row in rows
        ]


def to_float(valor: Any) -> float:
    if valor is None:
        return 0.0
    if isinstance(valor, Decimal):
        return float(valor)
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def normalizar_codigos_cuenta(codigos_cuenta: Iterable[str]) -> list[str]:
    codigos_normalizados: list[str] = []
    vistos = set()
    for codigo in codigos_cuenta:
        codigo_normalizado = str(codigo or "").strip()
        if not codigo_normalizado or codigo_normalizado in vistos:
            continue
        codigos_normalizados.append(codigo_normalizado)
        vistos.add(codigo_normalizado)
    return codigos_normalizados


def obtener_cuenta_neteada(codigo_cuenta: str) -> str | None:
    return MAPA_NETEO_CUENTAS.get(str(codigo_cuenta or "").strip())


def _mapa_neteo_sql() -> str:
    selects = [
        f"SELECT '{cuenta_total}' AS CuentaTotal, '{cuenta_neteada}' AS CuentaNeteada"
        for cuenta_total, cuenta_neteada in MAPA_NETEO_CUENTAS.items()
    ]
    return "\n    UNION ALL ".join(selects)

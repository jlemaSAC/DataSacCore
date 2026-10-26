from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class CorteCaptaciones:
    fecha: date
    filas: list[dict[str, Any]]


class SqlControlDiarioCaptacionesRepository:
    """Ingresos por creación del DPF que permanece en el universo del resumen al corte."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_diario(
        self, *, fecha_inicio: date, fecha_fin: date, fecha_sistema: date, id_agencia: int
    ) -> CorteCaptaciones | None:
        corte = self.db.execute(text("""
            SELECT TOP (1) CAST(CS.FECHASISTEMA AS date) AS fecha,
                C.FECHACIERREPLAZO AS cierre
            FROM GENERAL.CALENDARIO_SISTEMA AS CS
            LEFT JOIN GENERAL.EMPRESA_CIERREHISTORICO AS C
                ON CAST(C.FECHASISTEMA AS date) = CAST(CS.FECHASISTEMA AS date)
            WHERE CS.FECHASISTEMA >= :inicio_mes
              AND CS.FECHASISTEMA < :hasta_exclusivo
            ORDER BY CS.FECHASISTEMA DESC
        """), {
            "inicio_mes": fecha_fin.replace(day=1),
            "hasta_exclusivo": fecha_fin + timedelta(days=1),
        }).mappings().first()
        if corte is None:
            return None
        fecha_real = corte["fecha"]
        if isinstance(fecha_real, datetime):
            fecha_real = fecha_real.date()
        en_linea = fecha_real == fecha_sistema
        if not en_linea and corte["cierre"] is None:
            return None

        # Solo cambia la fuente temporal; fechas y agencia siempre se parametrizan.
        fuente = "INVERSION.DEPOSITO" if en_linea else "INVERSION.DEPOSITO FOR SYSTEM_TIME AS OF :cierre"
        filas = self.db.execute(text(f"""
            WITH Depositos AS (
                SELECT D.IDAGENCIA,
                    COALESCE(NULLIF(LTRIM(RTRIM(D.CODIGOUSUARIO)), ''), 'SIN USUARIO') AS codigo,
                    CAST(D.FECHACREACION AS date) AS fecha,
                    D.MONTO,
                    CASE WHEN EXISTS (
                        SELECT 1 FROM INVERSION.DEPOSITO_RENOVACION AS R
                        WHERE R.IDDEPOSITODESTINO = D.ID
                          AND R.FECHA >= :inicio_mes AND R.FECHA < :corte_exclusivo
                    ) THEN 'RENOVADO' ELSE 'NUEVO' END AS condicion
                FROM {fuente} AS D
                WHERE D.CODIGOESTADODEPOSITO IN ('A', 'E', 'V')
                  AND D.FECHACREACION >= :fecha_inicio
                  AND D.FECHACREACION < :hasta_exclusivo
                  AND (:id_agencia = 0 OR D.IDAGENCIA = :id_agencia)
                  AND EXISTS (
                      SELECT 1 FROM INVERSION.DEPOSITO_CLIENTE AS DC
                      INNER JOIN CLIENTES.CLIENTE AS C ON C.ID = DC.IDCLIENTE
                      INNER JOIN SUJETO.PERSONA AS P ON P.ID = C.IDPERSONA
                      WHERE DC.IDDEPOSITO = D.ID AND DC.ESPRINCIPAL = 1 AND DC.ACTIVO = 1
                  )
            ), Agrupados AS (
                SELECT IDAGENCIA, codigo, fecha, condicion, SUM(MONTO) AS monto
                FROM Depositos
                GROUP BY IDAGENCIA, codigo, fecha, condicion
            )
            SELECT X.*, COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), ''), 'SIN DATOS') AS agencia,
                COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), ''), X.codigo) AS nombre,
                COALESCE(NULLIF(LTRIM(RTRIM(Cargo.nombre)), ''), 'SIN CARGO') AS cargo
            FROM Agrupados AS X
            LEFT JOIN GENERAL.AGENCIA AS A ON A.ID = X.IDAGENCIA
            LEFT JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = X.codigo
            OUTER APPLY (
                SELECT TOP (1) C.NOMBRE AS nombre
                FROM NOMINA.EMPLEADO_USUARIO AS EU
                INNER JOIN NOMINA.EMPLEADO AS E ON E.ID = EU.IDEMPLEADO
                INNER JOIN NOMINA.CARGO AS C ON C.ID = E.IDCARGO
                WHERE EU.CODIGOUSUARIO = X.codigo
                ORDER BY E.FECHAPROCESO DESC, E.ID DESC
            ) AS Cargo
            ORDER BY X.IDAGENCIA, X.codigo, X.fecha, X.condicion
        """), {
            "cierre": corte["cierre"], "id_agencia": id_agencia,
            "fecha_inicio": fecha_inicio, "hasta_exclusivo": fecha_fin + timedelta(days=1),
            "inicio_mes": fecha_real.replace(day=1),
            "corte_exclusivo": fecha_real + timedelta(days=1),
        }).mappings().all()
        return CorteCaptaciones(fecha_real, [dict(fila) for fila in filas])

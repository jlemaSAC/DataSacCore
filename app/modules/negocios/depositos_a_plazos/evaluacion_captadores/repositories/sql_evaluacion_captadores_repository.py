from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class CorteCaptadores:
    fecha: date
    filas: list[dict[str, Any]]


class SqlEvaluacionCaptadoresRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_corte(
        self, *, fecha: date, fecha_sistema: date, fecha_ingreso_desde: date, id_agencia: int
    ) -> CorteCaptadores | None:
        corte = self.db.execute(text("""
            SELECT TOP (1) CAST(CS.FECHASISTEMA AS date) AS fecha,
                CS.SECERRO AS cerrado, C.FECHACIERREPLAZO AS cierre
            FROM GENERAL.CALENDARIO_SISTEMA AS CS
            LEFT JOIN GENERAL.EMPRESA_CIERREHISTORICO AS C
                ON C.FECHASISTEMA = CS.FECHASISTEMA
            WHERE CS.FECHASISTEMA >= :inicio_mes
              AND CS.FECHASISTEMA < :hasta_exclusivo
            ORDER BY CS.FECHASISTEMA DESC
        """), {
            "inicio_mes": fecha.replace(day=1), "hasta_exclusivo": fecha + timedelta(days=1),
        }).mappings().first()
        if corte is None:
            return None
        fecha_real = corte["fecha"]
        if isinstance(fecha_real, datetime):
            fecha_real = fecha_real.date()
        en_linea = fecha_real == fecha_sistema and not corte["cerrado"]
        if not en_linea and corte["cierre"] is None:
            return None
        # Ambas fuentes conservan el código del captador y su agencia al corte.
        fuente = "INVERSION.DEPOSITO" if en_linea else "INVERSION.DEPOSITO FOR SYSTEM_TIME AS OF :cierre"
        filas = self.db.execute(text(f"""
            WITH Agrupados AS (
                SELECT D.IDAGENCIA,
                    COALESCE(NULLIF(LTRIM(RTRIM(D.CODIGOUSUARIO)), ''), 'SIN USUARIO') AS codigo,
                    SUM(D.MONTO) AS saldo,
                    COUNT(*) AS operaciones,
                    SUM(D.TASA + D.VARIACION_TASA) AS suma_tasas,
                    SUM(CASE WHEN D.FECHACREACION >= :ingreso_desde
                                  AND D.FECHACREACION < :ingreso_hasta
                             THEN 1 ELSE 0 END) AS operaciones_renovacion,
                    SUM(CASE WHEN D.FECHACREACION >= :ingreso_desde
                                  AND D.FECHACREACION < :ingreso_hasta
                             THEN D.TASA + D.VARIACION_TASA ELSE 0 END) AS suma_tasas_renovacion
                FROM {fuente} AS D
                WHERE D.CODIGOESTADODEPOSITO IN ('A', 'E', 'V')
                  AND (:id_agencia = 0 OR D.IDAGENCIA = :id_agencia)
                  AND EXISTS (
                      SELECT 1 FROM INVERSION.DEPOSITO_CLIENTE AS DC
                      INNER JOIN CLIENTES.CLIENTE AS C ON C.ID = DC.IDCLIENTE
                      INNER JOIN SUJETO.PERSONA AS P ON P.ID = C.IDPERSONA
                      WHERE DC.IDDEPOSITO = D.ID AND DC.ESPRINCIPAL = 1 AND DC.ACTIVO = 1
                  )
                GROUP BY D.IDAGENCIA, D.CODIGOUSUARIO
            )
            SELECT X.*, COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), ''), 'SIN AGENCIA') AS agencia,
                COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), ''), X.codigo) AS nombre,
                COALESCE(Cargo.nombre, 'SIN CARGO') AS cargo
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
            ORDER BY X.IDAGENCIA, X.codigo
        """), {
            "cierre": corte["cierre"], "id_agencia": id_agencia,
            "ingreso_desde": fecha_ingreso_desde,
            "ingreso_hasta": fecha_real + timedelta(days=1),
        }).mappings().all()
        return CorteCaptadores(fecha_real, [dict(fila) for fila in filas])

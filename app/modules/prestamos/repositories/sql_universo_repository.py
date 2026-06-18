from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class SqlUniversoPrestamosRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_prestamos_actuales(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        top_clause = f"TOP ({int(limit)}) " if limit is not None else ""
        stmt = text(
            f"""
            WITH RubrosCapital AS (
                SELECT
                    PR.IDPRESTAMO AS IdPrestamo,
                    CASE
                        WHEN COALESCE(PR.CALCULADO, 0) - COALESCE(PR.COBRADO, 0) > 0
                            THEN COALESCE(PR.CALCULADO, 0) - COALESCE(PR.COBRADO, 0)
                        ELSE 0
                    END AS PendienteCapital,
                    COALESCE(TV.ESNODEVENGA, 0) AS EsNoDevenga,
                    COALESCE(TV.ESVENCIDO, 0) AS EsVencido
                FROM COLOCACION.PRESTAMO_RUBRO PR WITH (NOLOCK)
                INNER JOIN COLOCACION.RUBRO R WITH (NOLOCK)
                    ON R.ID = PR.IDRUBRO
                INNER JOIN COLOCACION.TIPO_RUBRO TR WITH (NOLOCK)
                    ON TR.CODIGO = R.CODIGOTIPORUBRO
                   AND TR.ESCAPITAL = 1
                LEFT JOIN COLOCACION.PRESTAMO_RUBRO_CLASIFICACION PRC WITH (NOLOCK)
                    ON PRC.IDPRESTAMORUBRO = PR.ID
                LEFT JOIN COLOCACION.CLASIFICACION_CARTERA CC WITH (NOLOCK)
                    ON CC.ID = PRC.IDCLASIFICACIONCARTERA
                LEFT JOIN COLOCACION.TIPO_VENCIMIENTO TV WITH (NOLOCK)
                    ON TV.CODIGO = CC.CODIGOTIPOVENCIMIENTO
                WHERE COALESCE(PR.CALCULADO, 0) - COALESCE(PR.COBRADO, 0) > 0
            ),
            CapitalClasificado AS (
                SELECT
                    IdPrestamo,
                    SUM(CASE WHEN EsNoDevenga = 1 THEN PendienteCapital ELSE 0 END) AS CapitalNoDevenga,
                    SUM(CASE WHEN EsVencido = 1 THEN PendienteCapital ELSE 0 END) AS CapitalVencido
                FROM RubrosCapital
                GROUP BY IdPrestamo
            )
            SELECT {top_clause}
                P.ID AS IdPrestamo,
                P.NUMERO AS NumeroPrestamo,
                P.IDAGENCIA AS IdAgencia,
                A.NOMBRE AS Agencia,
                P.CODIGOESTADO AS CodigoEstadoPrestamo,
                EP.NOMBRE AS EstadoPrestamo,
                P.CODIGOUSUARIO AS CodigoAsesor,
                P.CODIGOUSUARIO AS CodigoUsuario,
                U.NOMBRE AS NombreAsesor,
                P.CALIFICACION AS Calificacion,
                P.CODIGOPRODUCTO AS Producto,
                P.CODIGOTIPOPRESTAMO AS TipoPrestamo,
                P.SALDO AS SaldoCapital,
                COALESCE(CC.CapitalNoDevenga, 0) AS CapitalNoDevenga,
                COALESCE(CC.CapitalVencido, 0) AS CapitalVencido,
                COALESCE(PC.DIASMORAACTUAL, 0) AS DiasVencidos,
                CASE WHEN DIF.IDPRESTAMO IS NULL THEN 0 ELSE 1 END AS EsDiferido
            FROM COLOCACION.PRESTAMO P WITH (NOLOCK)
            INNER JOIN GENERAL.AGENCIA A WITH (NOLOCK)
                ON A.ID = P.IDAGENCIA
            LEFT JOIN COLOCACION.ESTADO_PRESTAMO EP WITH (NOLOCK)
                ON EP.CODIGO = P.CODIGOESTADO
            LEFT JOIN SEGURIDAD.USUARIO U WITH (NOLOCK)
                ON U.USUARIO = P.CODIGOUSUARIO
            LEFT JOIN CapitalClasificado CC
                ON CC.IdPrestamo = P.ID
            LEFT JOIN COLOCACION.PRESTAMO_CONSOLIDADO PC WITH (NOLOCK)
                ON PC.IDPRESTAMO = P.ID
            LEFT JOIN (
                SELECT IDPRESTAMO
                FROM COLOCACION.PRESTAMO_CUOTADIFERIDA_AGREGADA WITH (NOLOCK)
                WHERE FECHASISTEMA >= '20241111'
                GROUP BY IDPRESTAMO
            ) DIF
                ON DIF.IDPRESTAMO = P.ID
            WHERE P.CODIGOESTADO <> 'C'
            ORDER BY P.ID
            """
        )

        rows = self.db.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

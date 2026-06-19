from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class SqlUniversoPrestamosRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_prestamos_actuales(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        top_clause = f"TOP ({int(limit)}) " if limit is not None else ""
        base_order_clause = "ORDER BY P.ID" if limit is not None else ""
        stmt = text(
            f"""
            WITH PrestamosBase AS (
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
                    P.SALDO AS SaldoCapital
                FROM COLOCACION.PRESTAMO P WITH (NOLOCK)
                INNER JOIN GENERAL.AGENCIA A WITH (NOLOCK)
                    ON A.ID = P.IDAGENCIA
                LEFT JOIN COLOCACION.ESTADO_PRESTAMO EP WITH (NOLOCK)
                    ON EP.CODIGO = P.CODIGOESTADO
                LEFT JOIN SEGURIDAD.USUARIO U WITH (NOLOCK)
                    ON U.USUARIO = P.CODIGOUSUARIO
                WHERE P.CODIGOESTADO <> 'C'
                {base_order_clause}
            ),
            RubrosCapital AS (
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
                INNER JOIN PrestamosBase PB
                    ON PB.IdPrestamo = PR.IDPRESTAMO
                WHERE COALESCE(PR.CALCULADO, 0) - COALESCE(PR.COBRADO, 0) > 0
            ),
            CapitalClasificado AS (
                SELECT
                    IdPrestamo,
                    SUM(CASE WHEN EsNoDevenga = 1 THEN PendienteCapital ELSE 0 END) AS CapitalNoDevenga,
                    SUM(CASE WHEN EsVencido = 1 THEN PendienteCapital ELSE 0 END) AS CapitalVencido
                FROM RubrosCapital
                GROUP BY IdPrestamo
            ),
            RubrosExigibles AS (
                SELECT
                    PR.IDPRESTAMO AS IdPrestamo,
                    CASE
                        WHEN COALESCE(PR.CALCULADO, 0) - COALESCE(PR.COBRADO, 0) > 0
                            THEN COALESCE(PR.CALCULADO, 0) - COALESCE(PR.COBRADO, 0)
                        ELSE 0
                    END AS Pendiente,
                    COALESCE(TR.ESCAPITAL, 0) AS EsCapital,
                    COALESCE(TR.ESTASA, 0) AS EsInteres,
                    COALESCE(TR.ESMORA, 0) AS EsMora
                FROM COLOCACION.PRESTAMO_RUBRO PR WITH (NOLOCK)
                INNER JOIN COLOCACION.RUBRO R WITH (NOLOCK)
                    ON R.ID = PR.IDRUBRO
                INNER JOIN COLOCACION.TIPO_RUBRO TR WITH (NOLOCK)
                    ON TR.CODIGO = R.CODIGOTIPORUBRO
                INNER JOIN PrestamosBase PB
                    ON PB.IdPrestamo = PR.IDPRESTAMO
                WHERE COALESCE(PR.CALCULADO, 0) - COALESCE(PR.COBRADO, 0) > 0
                  AND PR.FECHAFIN <= CAST(GETDATE() AS date)
            ),
            ExigiblesClasificados AS (
                SELECT
                    IdPrestamo,
                    SUM(CASE WHEN EsCapital = 1 THEN Pendiente ELSE 0 END) AS ExigibleCapital,
                    SUM(CASE WHEN EsInteres = 1 THEN Pendiente ELSE 0 END) AS ExigibleInteres,
                    SUM(CASE WHEN EsMora = 1 THEN Pendiente ELSE 0 END) AS ExigibleMora,
                    SUM(
                        CASE
                            WHEN EsCapital = 0 AND EsInteres = 0 AND EsMora = 0 THEN Pendiente
                            ELSE 0
                        END
                    ) AS ExigibleOtros
                FROM RubrosExigibles
                GROUP BY IdPrestamo
            ),
            Diferidos AS (
                SELECT D.IDPRESTAMO AS IdPrestamo
                FROM COLOCACION.PRESTAMO_CUOTADIFERIDA_AGREGADA D WITH (NOLOCK)
                INNER JOIN PrestamosBase PB
                    ON PB.IdPrestamo = D.IDPRESTAMO
                WHERE D.FECHASISTEMA >= '20241111'
                GROUP BY D.IDPRESTAMO
            )
            SELECT
                PB.IdPrestamo,
                PB.NumeroPrestamo,
                PB.IdAgencia,
                PB.Agencia,
                PB.CodigoEstadoPrestamo,
                PB.EstadoPrestamo,
                PB.CodigoAsesor,
                PB.CodigoUsuario,
                PB.NombreAsesor,
                PB.Calificacion,
                PB.Producto,
                PB.TipoPrestamo,
                PB.SaldoCapital,
                COALESCE(CC.CapitalNoDevenga, 0) AS CapitalNoDevenga,
                COALESCE(CC.CapitalVencido, 0) AS CapitalVencido,
                COALESCE(PC.DIASMORAACTUAL, 0) AS DiasVencidos,
                COALESCE(EC.ExigibleCapital, 0) AS ExigibleCapital,
                COALESCE(EC.ExigibleInteres, 0) AS ExigibleInteres,
                COALESCE(EC.ExigibleMora, 0) AS ExigibleMora,
                COALESCE(EC.ExigibleOtros, 0) AS ExigibleOtros,
                COALESCE(PC.VALORALDIA, 0) AS ValorParaEstarAlDia,
                COALESCE(PC.VALORALDIAMASCUOTACTUAL, 0) AS ValorHastaCuotaActual,
                COALESCE(PC.VALORCANCELAPRESTAMO, 0) AS ValorCancelarTotal,
                CASE WHEN DIF.IdPrestamo IS NULL THEN 0 ELSE 1 END AS EsDiferido
            FROM PrestamosBase PB
            LEFT JOIN CapitalClasificado CC
                ON CC.IdPrestamo = PB.IdPrestamo
            LEFT JOIN ExigiblesClasificados EC
                ON EC.IdPrestamo = PB.IdPrestamo
            LEFT JOIN COLOCACION.PRESTAMO_CONSOLIDADO PC WITH (NOLOCK)
                ON PC.IDPRESTAMO = PB.IdPrestamo
            LEFT JOIN Diferidos DIF
                ON DIF.IdPrestamo = PB.IdPrestamo
            ORDER BY PB.IdPrestamo
            """
        )

        rows = self.db.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

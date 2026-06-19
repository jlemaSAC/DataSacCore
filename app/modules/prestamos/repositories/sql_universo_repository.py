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
            SET NOCOUNT ON;

            IF OBJECT_ID('tempdb..#PrestamosBase') IS NOT NULL
                DROP TABLE #PrestamosBase;
            IF OBJECT_ID('tempdb..#RubrosPendientes') IS NOT NULL
                DROP TABLE #RubrosPendientes;

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
            INTO #PrestamosBase
            FROM COLOCACION.PRESTAMO P WITH (NOLOCK)
            INNER JOIN GENERAL.AGENCIA A WITH (NOLOCK)
                ON A.ID = P.IDAGENCIA
            LEFT JOIN COLOCACION.ESTADO_PRESTAMO EP WITH (NOLOCK)
                ON EP.CODIGO = P.CODIGOESTADO
            LEFT JOIN SEGURIDAD.USUARIO U WITH (NOLOCK)
                ON U.USUARIO = P.CODIGOUSUARIO
            WHERE P.CODIGOESTADO <> 'C'
            {base_order_clause};

            CREATE UNIQUE CLUSTERED INDEX IX_PrestamosBase_IdPrestamo
                ON #PrestamosBase (IdPrestamo);

            SELECT
                PR.IDPRESTAMO AS IdPrestamo,
                CASE
                    WHEN COALESCE(PR.CALCULADO, 0) - COALESCE(PR.COBRADO, 0) > 0
                        THEN COALESCE(PR.CALCULADO, 0) - COALESCE(PR.COBRADO, 0)
                    ELSE 0
                END AS Pendiente,
                COALESCE(TR.ESCAPITAL, 0) AS EsCapital,
                COALESCE(TR.ESTASA, 0) AS EsInteres,
                COALESCE(TR.ESMORA, 0) AS EsMora,
                COALESCE(TV.ESNODEVENGA, 0) AS EsNoDevenga,
                COALESCE(TV.ESVENCIDO, 0) AS EsVencido,
                CASE WHEN PR.FECHAFIN <= CAST(GETDATE() AS date) THEN 1 ELSE 0 END AS EsExigible
            INTO #RubrosPendientes
            FROM COLOCACION.PRESTAMO_RUBRO PR WITH (NOLOCK)
            INNER JOIN #PrestamosBase PB
                ON PB.IdPrestamo = PR.IDPRESTAMO
            INNER JOIN COLOCACION.RUBRO R WITH (NOLOCK)
                ON R.ID = PR.IDRUBRO
            INNER JOIN COLOCACION.TIPO_RUBRO TR WITH (NOLOCK)
                ON TR.CODIGO = R.CODIGOTIPORUBRO
            LEFT JOIN COLOCACION.PRESTAMO_RUBRO_CLASIFICACION PRC WITH (NOLOCK)
                ON PRC.IDPRESTAMORUBRO = PR.ID
            LEFT JOIN COLOCACION.CLASIFICACION_CARTERA CC WITH (NOLOCK)
                ON CC.ID = PRC.IDCLASIFICACIONCARTERA
            LEFT JOIN COLOCACION.TIPO_VENCIMIENTO TV WITH (NOLOCK)
                ON TV.CODIGO = CC.CODIGOTIPOVENCIMIENTO
            WHERE COALESCE(PR.CALCULADO, 0) - COALESCE(PR.COBRADO, 0) > 0;

            CREATE NONCLUSTERED INDEX IX_RubrosPendientes_IdPrestamo
                ON #RubrosPendientes (IdPrestamo);

            WITH CapitalClasificado AS (
                SELECT
                    IdPrestamo,
                    SUM(CASE WHEN EsCapital = 1 AND EsNoDevenga = 1 THEN Pendiente ELSE 0 END) AS CapitalNoDevenga,
                    SUM(CASE WHEN EsCapital = 1 AND EsVencido = 1 THEN Pendiente ELSE 0 END) AS CapitalVencido
                FROM #RubrosPendientes
                GROUP BY IdPrestamo
            ),
            ExigiblesClasificados AS (
                SELECT
                    IdPrestamo,
                    SUM(CASE WHEN EsCapital = 1 AND EsExigible = 1 THEN Pendiente ELSE 0 END) AS ExigibleCapital,
                    SUM(CASE WHEN EsInteres = 1 AND EsExigible = 1 THEN Pendiente ELSE 0 END) AS ExigibleInteres,
                    SUM(CASE WHEN EsMora = 1 AND EsExigible = 1 THEN Pendiente ELSE 0 END) AS ExigibleMora,
                    SUM(
                        CASE
                            WHEN EsCapital = 0 AND EsInteres = 0 AND EsMora = 0 AND EsExigible = 1 THEN Pendiente
                            ELSE 0
                        END
                    ) AS ExigibleOtros
                FROM #RubrosPendientes
                GROUP BY IdPrestamo
            ),
            Diferidos AS (
                SELECT D.IDPRESTAMO AS IdPrestamo
                FROM COLOCACION.PRESTAMO_CUOTADIFERIDA_AGREGADA D WITH (NOLOCK)
                INNER JOIN #PrestamosBase PB
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
                COALESCE(UC.CalificacionProvision, PB.Calificacion) AS Calificacion,
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
                COALESCE(UC.SaldoBaseProvision, 0) AS SaldoBaseProvision,
                COALESCE(UC.PorcentajeProvisionFuente, 0) AS PorcentajeProvisionFuente,
                COALESCE(CPI.PORCENTAJE_FIJO, 0) AS PorcentajeProvisionReglaFijo,
                COALESCE(CPI.PORCENTAJE_MINIMO, 0) AS PorcentajeProvisionMinimo,
                COALESCE(CPI.PORCENTAJE_MAXIMO, 0) AS PorcentajeProvisionMaximo,
                COALESCE(CPI.ESPORCENTAJE_FIJO, 0) AS EsPorcentajeFijo,
                COALESCE(UC.ProvisionAutomatica, 0) AS ProvisionAutomatica,
                COALESCE(UC.ProvisionManual, 0) AS ProvisionManual,
                COALESCE(UC.ProvisionRequeridaFuente, 0) AS ProvisionRequeridaFuente,
                COALESCE(UC.ProvisionConstituida, 0) AS ProvisionConstituida,
                CASE WHEN DIF.IdPrestamo IS NULL THEN 0 ELSE 1 END AS EsDiferido
            FROM #PrestamosBase PB
            LEFT JOIN CapitalClasificado CC
                ON CC.IdPrestamo = PB.IdPrestamo
            LEFT JOIN ExigiblesClasificados EC
                ON EC.IdPrestamo = PB.IdPrestamo
            LEFT JOIN COLOCACION.PRESTAMO_CONSOLIDADO PC WITH (NOLOCK)
                ON PC.IDPRESTAMO = PB.IdPrestamo
            OUTER APPLY (
                SELECT TOP 1
                    PCAL.CALIFICACION AS CalificacionProvision,
                    PCAL.SALDO AS SaldoBaseProvision,
                    PCAL.PORCENTAJE_FIJO AS PorcentajeProvisionFuente,
                    PCAL.PROVISIONAUTOMATICA AS ProvisionAutomatica,
                    PCAL.PROVISIONMANUAL AS ProvisionManual,
                    COALESCE(PCAL.PROVISIONAUTOMATICA, 0)
                        + COALESCE(PCAL.PROVISIONMANUAL, 0) AS ProvisionRequeridaFuente,
                    PCAL.PROVISIONCONSTITUIDA AS ProvisionConstituida,
                    PCAL.IDCALIFICACIONPRESTAMOINFORMACION AS IdCalificacionPrestamoInformacion
                FROM COLOCACION.PRESTAMO_CALIFICACION PCAL WITH (NOLOCK)
                WHERE PCAL.IDPRESTAMO = PB.IdPrestamo
                ORDER BY PCAL.FECHACALIFICACION DESC, PCAL.ID DESC
            ) UC
            LEFT JOIN COLOCACION.CALIFICACION_PRESTAMO_INFORMACION CPI WITH (NOLOCK)
                ON CPI.ID = UC.IdCalificacionPrestamoInformacion
            LEFT JOIN Diferidos DIF
                ON DIF.IdPrestamo = PB.IdPrestamo
            ORDER BY PB.IdPrestamo
            """
        )

        rows = self.db.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

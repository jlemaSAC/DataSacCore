from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


class SqlRecuperacionHistoricoRepository:
    """Obtiene el contexto vigente solo para recuperaciones de la fecha actual."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_prestamos_actuales(self, numeros_prestamo: set[str]) -> dict[str, dict[str, Any]]:
        if not numeros_prestamo:
            return {}

        statement = (
            text(
                """
                SELECT
                    P.NUMERO AS NumeroPrestamo,
                    A.NOMBRE AS Agencia,
                    EP.NOMBRE AS EstadoPrestamo,
                    COALESCE(TE.NOMBRE, 'NUEVO') AS TipoCondicion,
                    PRD.NOMBRE AS Producto,
                    TP.NOMBRE AS TipoPrestamo,
                    U.NOMBRE AS NombreAsesor,
                    CC.NOMBRE AS Segmento,
                    DPC.Provincia,
                    DPC.Canton,
                    DPC.Parroquia,
                    EDU.NOMBRE AS Educacion,
                    CASE
                        WHEN PN.FECHANACIMIENTO IS NULL THEN NULL
                        ELSE DATEDIFF(YEAR, PN.FECHANACIMIENTO, CAST(GETDATE() AS date))
                            - CASE
                                WHEN DATEADD(YEAR, DATEDIFF(YEAR, PN.FECHANACIMIENTO, CAST(GETDATE() AS date)), PN.FECHANACIMIENTO)
                                     > CAST(GETDATE() AS date)
                                THEN 1 ELSE 0
                              END
                    END AS Edad,
                    CASE
                        WHEN EXISTS (
                            SELECT 1
                            FROM COLOCACION.PRESTAMO_GARANTIAHIPOTECARIA AS PGH WITH (NOLOCK)
                            WHERE PGH.IDPRESTAMO = P.ID AND PGH.ACTIVO = 1
                        ) THEN 'HIPOTECARIA'
                        WHEN EXISTS (
                            SELECT 1
                            FROM COLOCACION.PRESTAMO_GARANTIAPRENDARIA AS PGP WITH (NOLOCK)
                            WHERE PGP.IDPRESTAMO = P.ID AND PGP.ACTIVO = 1
                        ) THEN 'PRENDARIA'
                        WHEN EXISTS (
                            SELECT 1
                            FROM COLOCACION.PRESTAMO_GARANTIAPERSONAL AS PGPE WITH (NOLOCK)
                            WHERE PGPE.IDPRESTAMO = P.ID AND PGPE.ACTIVO = 1
                        ) THEN 'SOBRE FIRMAS'
                        WHEN EXISTS (
                            SELECT 1
                            FROM COLOCACION.PRESTAMO_GARANTIAINVERSION AS PGI WITH (NOLOCK)
                            WHERE PGI.IDPRESTAMO = P.ID AND PGI.ACTIVO = 1
                        ) THEN 'GARANTIA DE INVERSION'
                        ELSE 'SOBRE FIRMAS'
                    END AS TipoDeGarantia,
                    P.DEUDAINICIAL AS DeudaInicial,
                    P.TASA AS TasaNominal,
                    P.TEA AS TasaAnual,
                    P.CUOTAS AS Plazo
                FROM COLOCACION.PRESTAMO AS P WITH (NOLOCK)
                LEFT JOIN GENERAL.AGENCIA AS A WITH (NOLOCK)
                    ON A.ID = P.IDAGENCIA
                LEFT JOIN COLOCACION.ESTADO_PRESTAMO AS EP WITH (NOLOCK)
                    ON EP.CODIGO = P.CODIGOESTADO
                LEFT JOIN CREDITO.TIPO_PRESTAMO AS TP WITH (NOLOCK)
                    ON TP.CODIGO = P.CODIGOTIPOPRESTAMO
                LEFT JOIN FINANCIERO.PRODUCTO AS PRD WITH (NOLOCK)
                    ON PRD.CODIGO = P.CODIGOPRODUCTO
                LEFT JOIN SEGURIDAD.USUARIO AS U WITH (NOLOCK)
                    ON U.USUARIO = P.CODIGOUSUARIO
                LEFT JOIN CREDITO.CALIFICACION_CONTABLE_SEGMENTO AS CCS WITH (NOLOCK)
                    ON CCS.ID = P.IDCALIFICACIONCONTABLESEGMENTO
                LEFT JOIN CREDITO.CALIFICACION_CONTABLE AS CC WITH (NOLOCK)
                    ON CC.CODIGO = CCS.CODIGOCALIFICACIONCONTABLE
                OUTER APPLY (
                    SELECT TOP 1
                        PER.IDRESIDENCIA,
                        PN.FECHANACIMIENTO,
                        PN.CODIGOEDUCACION
                    FROM COLOCACION.PRESTAMO_CLIENTE AS PCLI WITH (NOLOCK)
                    INNER JOIN CLIENTES.CLIENTE AS CLI WITH (NOLOCK)
                        ON CLI.ID = PCLI.IDCLIENTE
                    INNER JOIN SUJETO.PERSONA AS PER WITH (NOLOCK)
                        ON PER.ID = CLI.IDPERSONA
                    LEFT JOIN SUJETO.PERSONA_NATURAL AS PN WITH (NOLOCK)
                        ON PN.IDPERSONA = PER.ID
                    WHERE PCLI.IDPRESTAMO = P.ID
                      AND PCLI.ACTIVO = 1
                    ORDER BY PCLI.ESPRINCIPAL DESC, PCLI.ID ASC
                ) AS PN
                LEFT JOIN GENERAL.DIVISIONPOLITICA_CONSOLIDADO AS DPC WITH (NOLOCK)
                    ON DPC.IDDIVISIONNIVELBAJO = PN.IDRESIDENCIA
                LEFT JOIN SUJETO.EDUCACION AS EDU WITH (NOLOCK)
                    ON EDU.CODIGO = PN.CODIGOEDUCACION
                LEFT JOIN COLOCACION.PRESTAMO_SOLICITUD AS PS WITH (NOLOCK)
                    ON PS.IDPRESTAMO = P.ID
                LEFT JOIN CREDITO.SOLICITUD_PRESTAMO_TIPOEMISION AS SPTE WITH (NOLOCK)
                    ON SPTE.IDSOLICITUD = PS.IDSOLICITUD
                LEFT JOIN CREDITO.TIPO_EMISION AS TE WITH (NOLOCK)
                    ON TE.CODIGO = SPTE.CODIGOTIPOEMISION
                WHERE P.NUMERO IN :numeros_prestamo
                """
            )
            .bindparams(bindparam("numeros_prestamo", expanding=True))
        )
        rows = self.db.execute(
            statement,
            {"numeros_prestamo": sorted(numeros_prestamo)},
        ).mappings()
        return {
            str(row["NumeroPrestamo"]): dict(row)
            for row in rows
            if row.get("NumeroPrestamo") is not None
        }

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.modules.negocios.recuperacion.resumen.domain import (
    DatosOperativosRecuperacion,
)


class SqlDetalleRecuperacionRepository:
    """Enriquece únicamente los préstamos de la página con su estado vigente."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_datos_actuales(
        self,
        numeros_prestamo: list[str],
    ) -> dict[str, DatosOperativosRecuperacion]:
        if not numeros_prestamo:
            return {}

        statement = text(
            """
            WITH PrestamosPagina AS (
                SELECT
                    P.ID,
                    P.NUMERO,
                    P.CODIGOESTADO,
                    P.CALIFICACION,
                    P.SALDO,
                    P.CUOTAS
                FROM COLOCACION.PRESTAMO AS P WITH (NOLOCK)
                WHERE P.NUMERO IN :numeros_prestamo
            ),
            Cuotas AS (
                SELECT
                    PR.IDPRESTAMO,
                    SUM(CASE
                        WHEN PR.IDRUBRO = 1 AND PR.CODIGOESTADO = 'C' THEN 1
                        ELSE 0
                    END) AS CuotasPagadas
                FROM COLOCACION.PRESTAMO_RUBRO AS PR WITH (NOLOCK)
                INNER JOIN PrestamosPagina AS PP ON PP.ID = PR.IDPRESTAMO
                GROUP BY PR.IDPRESTAMO
            ),
            Diferidos AS (
                SELECT D.IDPRESTAMO
                FROM COLOCACION.PRESTAMO_CUOTADIFERIDA_AGREGADA AS D WITH (NOLOCK)
                INNER JOIN PrestamosPagina AS PP ON PP.ID = D.IDPRESTAMO
                WHERE D.FECHASISTEMA >= '20241111'
                GROUP BY D.IDPRESTAMO
            )
            SELECT
                PP.NUMERO AS NumeroPrestamo,
                Principal.NumeroSocio,
                COALESCE(Principal.Nombre, 'SIN DATOS') AS Nombre,
                COALESCE(EP.NOMBRE, PP.CODIGOESTADO, 'SIN DATOS') AS EstadoPrestamo,
                COALESCE(PP.CALIFICACION, 'SIN DATOS') AS CalificacionActual,
                COALESCE(PP.SALDO, 0) AS SaldoCapital,
                COALESCE(PC.VALORALDIA, 0) AS PendientePago,
                COALESCE(PC.VALORALDIAMASCUOTACTUAL, 0) AS ValorAlDiaMasCuotaActual,
                COALESCE(C.CuotasPagadas, 0) AS CuotasPagadas,
                COALESCE(PP.CUOTAS, 0) AS TotalCuotas,
                CASE WHEN D.IDPRESTAMO IS NULL THEN 0 ELSE 1 END AS EsDiferido
            FROM PrestamosPagina AS PP
            LEFT JOIN COLOCACION.ESTADO_PRESTAMO AS EP WITH (NOLOCK)
                ON EP.CODIGO = PP.CODIGOESTADO
            LEFT JOIN COLOCACION.PRESTAMO_CONSOLIDADO AS PC WITH (NOLOCK)
                ON PC.IDPRESTAMO = PP.ID
            LEFT JOIN Cuotas AS C ON C.IDPRESTAMO = PP.ID
            LEFT JOIN Diferidos AS D ON D.IDPRESTAMO = PP.ID
            OUTER APPLY (
                SELECT TOP 1
                    CLI.NUMERO AS NumeroSocio,
                    PER.NOMBRE AS Nombre
                FROM COLOCACION.PRESTAMO_CLIENTE AS PCLI WITH (NOLOCK)
                INNER JOIN CLIENTES.CLIENTE AS CLI WITH (NOLOCK)
                    ON CLI.ID = PCLI.IDCLIENTE
                INNER JOIN SUJETO.PERSONA AS PER WITH (NOLOCK)
                    ON PER.ID = CLI.IDPERSONA
                WHERE PCLI.IDPRESTAMO = PP.ID
                  AND PCLI.ACTIVO = 1
                ORDER BY PCLI.ESPRINCIPAL DESC, PCLI.ID ASC
            ) AS Principal
            """
        ).bindparams(bindparam("numeros_prestamo", expanding=True))
        rows = self.db.execute(
            statement,
            {"numeros_prestamo": numeros_prestamo},
        ).mappings()
        return {
            str(row["NumeroPrestamo"]): DatosOperativosRecuperacion(
                numero_prestamo=str(row["NumeroPrestamo"]),
                socio=int(row["NumeroSocio"]) if row["NumeroSocio"] is not None else None,
                nombre=str(row["Nombre"] or "SIN DATOS"),
                estado_prestamo=str(row["EstadoPrestamo"] or "SIN DATOS"),
                calificacion_actual=str(row["CalificacionActual"] or "SIN DATOS"),
                saldo_capital=float(row["SaldoCapital"] or 0),
                pendiente_pago=float(row["PendientePago"] or 0),
                valor_al_dia_mas_cuota_actual=float(
                    row["ValorAlDiaMasCuotaActual"] or 0
                ),
                cuotas_pagadas=int(row["CuotasPagadas"] or 0),
                total_cuotas=int(row["TotalCuotas"] or 0),
                es_diferido=bool(row["EsDiferido"]),
            )
            for row in rows
            if row["NumeroPrestamo"] is not None
        }

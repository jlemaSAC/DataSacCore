from concurrent.futures import ThreadPoolExecutor
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.negocios.recuperacion.recaudacion_acumulada.domain import (
    DetalleCuotaPrestamo,
)


TAMANIO_LOTE_SQL = 500
MAX_TRABAJADORES_SQL = 5


class SqlDetalleCuotasRepository:
    """Obtiene por lotes los datos de cuotas que no existen en los snapshots."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_detalles(
        self,
        prestamos: list[dict[str, Any]],
    ) -> dict[str, DetalleCuotaPrestamo]:
        if not prestamos:
            return {}
        if len(prestamos) <= TAMANIO_LOTE_SQL:
            return self._obtener_detalles_lote(prestamos)

        bind = self.db.get_bind()
        lotes = [
            prestamos[indice : indice + TAMANIO_LOTE_SQL]
            for indice in range(0, len(prestamos), TAMANIO_LOTE_SQL)
        ]

        def consultar_lote(
            lote: list[dict[str, Any]],
        ) -> dict[str, DetalleCuotaPrestamo]:
            with Session(bind=bind) as session:
                return SqlDetalleCuotasRepository(session)._obtener_detalles_lote(lote)

        resultado: dict[str, DetalleCuotaPrestamo] = {}
        with ThreadPoolExecutor(
            max_workers=min(MAX_TRABAJADORES_SQL, len(lotes))
        ) as executor:
            for detalles_lote in executor.map(consultar_lote, lotes):
                resultado.update(detalles_lote)
        return resultado

    def _obtener_detalles_lote(
        self,
        prestamos: list[dict[str, Any]],
    ) -> dict[str, DetalleCuotaPrestamo]:

        statement = text(
            """
            SET NOCOUNT ON;

            SELECT
                Nodo.value('@numero', 'NVARCHAR(100)') AS NumeroPrestamo,
                Nodo.value('@provision', 'DECIMAL(18, 6)') AS ProvisionActual,
                Nodo.value('@saldo', 'DECIMAL(18, 6)') AS SaldoActual
            INTO #PrestamosSolicitados
            FROM (SELECT CAST(:prestamos_xml AS XML) AS Documento) AS Entrada
            CROSS APPLY Entrada.Documento.nodes('/prestamos/prestamo') AS Item(Nodo);

            CREATE UNIQUE CLUSTERED INDEX IX_PrestamosSolicitados_Numero
                ON #PrestamosSolicitados (NumeroPrestamo);

            SELECT
                P.ID AS IdPrestamo,
                P.NUMERO AS NumeroPrestamo,
                P.IDEMPRESA AS IdEmpresa,
                P.CUOTAS AS TotalCuotas,
                PS.ProvisionActual,
                PS.SaldoActual
            INTO #PrestamosBase
            FROM #PrestamosSolicitados AS PS
            INNER JOIN COLOCACION.PRESTAMO AS P WITH (NOLOCK)
                ON P.NUMERO = PS.NumeroPrestamo;

            CREATE UNIQUE CLUSTERED INDEX IX_PrestamosBase_Id
                ON #PrestamosBase (IdPrestamo);

            CREATE TABLE #SaldoPorCuota (
                IdPrestamo INT NOT NULL,
                NumeroCuota INT NOT NULL,
                SaldoCuota DECIMAL(18, 6) NOT NULL,
                CapitalPendienteCuota DECIMAL(18, 6) NOT NULL,
                Calificacion NVARCHAR(20) NULL,
                DiasMora INT NULL
            );

            INSERT INTO #SaldoPorCuota (
                IdPrestamo,
                NumeroCuota,
                SaldoCuota,
                CapitalPendienteCuota,
                Calificacion,
                DiasMora
            )
            SELECT
                PR.IDPRESTAMO,
                PR.NUMEROCUOTA,
                SUM(
                    ROUND(COALESCE(PR.CALCULADO, 0), 2)
                    - ROUND(COALESCE(PR.COBRADO, 0), 2)
                ),
                SUM(
                    CASE
                        WHEN TR.ESCAPITAL = 1
                        THEN ROUND(COALESCE(PR.CALCULADO, 0), 2)
                             - ROUND(COALESCE(PR.COBRADO, 0), 2)
                        ELSE 0
                    END
                ),
                MAX(CASE WHEN TR.ESCAPITAL = 1 THEN PRC.CALIFICACION END),
                MAX(CASE WHEN TR.ESCAPITAL = 1 THEN PRC.DIASMORA END)
            FROM #PrestamosBase AS PB
            INNER LOOP JOIN COLOCACION.PRESTAMO_RUBRO AS PR WITH (
                NOLOCK,
                INDEX(IX_PRESTAMO_RUBRO_IDPRESTAMO_1)
            )
                ON PR.IDPRESTAMO = PB.IdPrestamo
            INNER JOIN COLOCACION.RUBRO AS R WITH (NOLOCK)
                ON R.ID = PR.IDRUBRO
            INNER JOIN COLOCACION.TIPO_RUBRO AS TR WITH (NOLOCK)
                ON TR.CODIGO = R.CODIGOTIPORUBRO
            LEFT JOIN COLOCACION.PRESTAMO_RUBRO_CALIFICACION AS PRC WITH (NOLOCK)
                ON PRC.IDPRESTAMORUBRO = PR.ID
            WHERE ROUND(COALESCE(PR.CALCULADO, 0), 2)
                  - ROUND(COALESCE(PR.COBRADO, 0), 2) > 0
            GROUP BY PR.IDPRESTAMO, PR.NUMEROCUOTA
            OPTION (LOOP JOIN, RECOMPILE);

            CREATE UNIQUE CLUSTERED INDEX IX_SaldoPorCuota_PrestamoCuota
                ON #SaldoPorCuota (IdPrestamo, NumeroCuota);

            ;WITH CuotaActual AS (
                SELECT
                    SPC.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY SPC.IdPrestamo
                        ORDER BY SPC.NumeroCuota
                    ) AS Orden
                FROM #SaldoPorCuota AS SPC
            ),
            CuotasPendientes AS (
                SELECT IdPrestamo, COUNT(*) AS Cantidad
                FROM #SaldoPorCuota
                GROUP BY IdPrestamo
            ),
            SiguienteCuota AS (
                SELECT
                    CA.IdPrestamo,
                    MIN(SPC.NumeroCuota) AS NumeroCuota
                FROM CuotaActual AS CA
                INNER JOIN #SaldoPorCuota AS SPC
                    ON SPC.IdPrestamo = CA.IdPrestamo
                   AND SPC.NumeroCuota > CA.NumeroCuota
                WHERE CA.Orden = 1
                GROUP BY CA.IdPrestamo
            )
            SELECT
                PB.NumeroPrestamo,
                CA.NumeroCuota AS NumeroCuotaActualNoPagada,
                SC.NumeroCuota AS NumeroCuotaSiguiente,
                COALESCE(CA.SaldoCuota, 0) AS CobroHastaCuota,
                COALESCE(CS.Calificacion, 'A-1') AS CalificacionSimulada,
                COALESCE(CS.DiasMora, 0) AS DiasMoraSimulados,
                CASE
                    WHEN PB.SaldoActual - COALESCE(CA.CapitalPendienteCuota, 0) < 0 THEN 0
                    ELSE PB.SaldoActual - COALESCE(CA.CapitalPendienteCuota, 0)
                END AS SaldoSimulado,
                CASE
                    WHEN PB.TotalCuotas - COALESCE(CP.Cantidad, 0) < 0 THEN 0
                    ELSE PB.TotalCuotas - COALESCE(CP.Cantidad, 0)
                END AS CuotasPagadas,
                COALESCE(CP.Cantidad, 0) AS CuotasPendientes,
                PB.TotalCuotas,
                REGLA.PORCENTAJE_FIJO AS PorcentajeFijo,
                REGLA.PORCENTAJE_MINIMO AS PorcentajeMinimo,
                REGLA.PORCENTAJE_MAXIMO AS PorcentajeMaximo,
                REGLA.ESPORCENTAJE_FIJO AS EsPorcentajeFijo
            FROM #PrestamosBase AS PB
            LEFT JOIN CuotaActual AS CA
                ON CA.IdPrestamo = PB.IdPrestamo AND CA.Orden = 1
            LEFT JOIN CuotasPendientes AS CP
                ON CP.IdPrestamo = PB.IdPrestamo
            LEFT JOIN SiguienteCuota AS SC
                ON SC.IdPrestamo = PB.IdPrestamo
            LEFT JOIN #SaldoPorCuota AS CS
                ON CS.IdPrestamo = PB.IdPrestamo
               AND CS.NumeroCuota = SC.NumeroCuota
            OUTER APPLY (
                SELECT TOP (1)
                    CPI.PORCENTAJE_FIJO,
                    CPI.PORCENTAJE_MINIMO,
                    CPI.PORCENTAJE_MAXIMO,
                    CPI.ESPORCENTAJE_FIJO
                FROM COLOCACION.CALIFICACION_PRESTAMO_INFORMACION AS CPI WITH (NOLOCK)
                WHERE CPI.IDEMPRESA = PB.IdEmpresa
                  AND CPI.ACTIVO = 1
                  AND COALESCE(CS.DiasMora, 0) BETWEEN CPI.DIAINICIO AND CPI.DIAFIN
                  AND (
                      UPPER(LTRIM(RTRIM(CPI.CALIFICACION))) = UPPER(COALESCE(CS.Calificacion, 'A-1'))
                      OR NULLIF(LTRIM(RTRIM(CPI.CALIFICACION)), '') IS NULL
                  )
                ORDER BY
                    CASE WHEN UPPER(LTRIM(RTRIM(CPI.CALIFICACION))) =
                                   UPPER(COALESCE(CS.Calificacion, 'A-1'))
                         THEN 0 ELSE 1 END,
                    CPI.ID
            ) AS REGLA
            OPTION (RECOMPILE);
            """
        )
        payload = _prestamos_xml(prestamos)
        rows = self.db.execute(statement, {"prestamos_xml": payload}).mappings()
        resultado: dict[str, DetalleCuotaPrestamo] = {}
        for row in rows:
            numero = str(row["NumeroPrestamo"])
            resultado[numero] = DetalleCuotaPrestamo(
                numero_prestamo=numero,
                socio=_entero_opcional(row.get("Socio")),
                nombre=_texto(row.get("Nombre")),
                identificacion=_texto(row.get("Identificacion")),
                provincia=_texto(row.get("Provincia")),
                canton=_texto(row.get("Canton")),
                parroquia=_texto(row.get("Parroquia")),
                direccion=_texto(row.get("Direccion")),
                telefonos=_texto(row.get("Telefonos")),
                numero_cuota_actual_no_pagada=_entero_opcional(
                    row.get("NumeroCuotaActualNoPagada")
                ),
                numero_cuota_siguiente=_entero_opcional(
                    row.get("NumeroCuotaSiguiente")
                ),
                cobro_hasta_cuota=float(row.get("CobroHastaCuota") or 0),
                calificacion_con_cobro_una_cuota=_texto(
                    row.get("CalificacionSimulada"), "A-1"
                ),
                dias_mora_con_cobro_una_cuota=int(row.get("DiasMoraSimulados") or 0),
                saldo_capital_con_cobro_una_cuota=float(row.get("SaldoSimulado") or 0),
                cuotas_pendientes=int(row.get("CuotasPendientes") or 0),
                cuotas_pagadas=int(row.get("CuotasPagadas") or 0),
                total_cuotas=int(row.get("TotalCuotas") or 0),
                porcentaje_fijo=_float_opcional(row.get("PorcentajeFijo")),
                porcentaje_minimo=_float_opcional(row.get("PorcentajeMinimo")),
                porcentaje_maximo=_float_opcional(row.get("PorcentajeMaximo")),
                es_porcentaje_fijo=(
                    bool(row.get("EsPorcentajeFijo"))
                    if row.get("EsPorcentajeFijo") is not None
                    else None
                ),
                garante_1=_garante(row, "G1"),
                garante_2=_garante(row, "G2"),
            )
        return resultado


def _texto(valor: Any, default: str = "") -> str:
    texto = str(valor or "").strip()
    return texto or default


def _entero_opcional(valor: Any) -> int | None:
    try:
        return int(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def _float_opcional(valor: Any) -> float | None:
    try:
        return float(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def _garante(row: Any, prefijo: str) -> dict[str, str] | None:
    identificacion = _texto(row.get(f"{prefijo}Identificacion"))
    nombres = _texto(row.get(f"{prefijo}Nombres"))
    if not identificacion and not nombres:
        return None
    return {
        "identificacion": identificacion,
        "nombres": nombres,
        "provincia": _texto(row.get(f"{prefijo}Provincia")),
        "canton": _texto(row.get(f"{prefijo}Canton")),
        "parroquia": _texto(row.get(f"{prefijo}Parroquia")),
        "direccion": _texto(row.get(f"{prefijo}Direccion")),
        "telefonos": _texto(row.get(f"{prefijo}Telefonos")),
    }


def _prestamos_xml(prestamos: list[dict[str, Any]]) -> str:
    raiz = Element("prestamos")
    for prestamo in prestamos:
        SubElement(
            raiz,
            "prestamo",
            numero=str(prestamo["numero_prestamo"]),
            provision=str(float(prestamo.get("provision_actual") or 0)),
            saldo=str(float(prestamo.get("saldo_actual") or 0)),
        )
    return tostring(raiz, encoding="unicode")

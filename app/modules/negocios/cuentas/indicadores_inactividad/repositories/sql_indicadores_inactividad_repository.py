from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ...sql_cuentas import (
    AGENCIA_EXPANDIBLE,
    SALDOS_POR_CUENTA,
    TABLAS_CUENTA_BASE,
    secuencia_inactivacion,
)
from ..constantes import RANGOS_EDAD


_TITULAR_PRINCIPAL = """
    OUTER APPLY (
        SELECT TOP (1) CL.ID AS id_cliente, PN.FECHANACIMIENTO, PN.ESMASCULINO,
               EC.NOMBRE AS estado_civil
        FROM AHORROS.CUENTA_CLIENTE AS CC
        INNER JOIN CLIENTES.CLIENTE AS CL ON CL.ID = CC.IDCLIENTE
        LEFT JOIN SUJETO.PERSONA_NATURAL AS PN ON PN.IDPERSONA = CL.IDPERSONA
        LEFT JOIN SUJETO.ESTADO_CIVIL AS EC ON EC.CODIGO = PN.CODIGOESTADOCIVIL
        WHERE CC.NUMEROCUENTA = B.NUMERO AND CC.PRINCIPAL = 1
          AND B.saldo > 0 AND :incluir_analisis = 1
        ORDER BY CC.IDCLIENTE, CC.ID
    ) AS T
    CROSS APPLY (VALUES (
        CAST(T.FECHANACIMIENTO AS date),
        DATEDIFF(year, T.FECHANACIMIENTO, :fecha_sistema)
    )) AS N(nacimiento, anios)
    OUTER APPLY (
        SELECT TOP (1) 1 AS socio
        FROM AHORROS.CUENTA_CLIENTE AS CC
        INNER JOIN AHORROS.CUENTA AS CERT ON CERT.NUMERO = CC.NUMEROCUENTA
        INNER JOIN AHORROS.TIPO_CUENTA AS TIPO ON TIPO.CODIGO = CERT.CODIGOTIPOCUENTA
        WHERE CC.IDCLIENTE = T.id_cliente AND CC.PRINCIPAL = 1
          AND TIPO.ESCERTIFICADOAPORTACION = 1
          AND CERT.CODIGOESTADO NOT IN (N'C', N'N', N'P')
    ) AS M
"""

_DATOS_TITULAR = """
    CASE WHEN N.nacimiento <= :fecha_sistema THEN N.anios -
         CASE WHEN DATEADD(year, N.anios, N.nacimiento) > :fecha_sistema THEN 1 ELSE 0 END
    END AS edad,
    CASE T.ESMASCULINO WHEN 1 THEN N'Hombre' WHEN 0 THEN N'Mujer' END AS sexo,
    NULLIF(LTRIM(RTRIM(T.estado_civil)), N'') AS estado_civil,
    CASE WHEN T.id_cliente IS NULL THEN NULL
         WHEN M.socio = 1 THEN N'Socio' ELSE N'No socio'
    END AS socio
"""

_RANGOS_EDAD_SQL = "\n                   ".join(
    f"WHEN edad BETWEEN {menor} AND {mayor} THEN {menor}" for menor, mayor in RANGOS_EDAD
)

_CONSULTA = """
    WITH CuentasCandidatas AS (
        SELECT C.NUMERO, C.IDAGENCIA, C.CODIGOESTADO, C.FECHAULTIMATRANSACCIONACTIVA, C.FECHACREACION
        {tablas_cuenta}
        WHERE C.CODIGOESTADO = N'I' AND TC.ESCERTIFICADOAPORTACION = 0
          AND C.IDAGENCIA IN :ids_agencia
    ),
    {historial}
    Base AS (
        SELECT C.NUMERO, C.IDAGENCIA AS id_agencia,
               COALESCE(A.NOMBRE, N'No especificado') AS agencia,
               CASE WHEN CAST(C.FECHAULTIMATRANSACCIONACTIVA AS date) <= :fecha_sistema
                    THEN CAST(C.FECHAULTIMATRANSACCIONACTIVA AS date)
               END AS ultima_transaccion,
               CASE WHEN CAST(C.FECHACREACION AS date) <= :fecha_sistema
                    THEN CONVERT(char(7), C.FECHACREACION, 126)
               END AS mes_apertura,
               COALESCE(S.total, 0) AS saldo
        FROM CuentasCandidatas AS C
        LEFT JOIN GENERAL.AGENCIA AS A ON A.ID = C.IDAGENCIA
        {saldos_cuenta}
    ), Datos AS (
        SELECT B.*,
               CASE WHEN B.saldo > 0 AND :incluir_analisis = 1
                    THEN DATEDIFF(day, B.ultima_transaccion, :fecha_sistema)
               END AS dias,
               {dias_inactivacion} AS dias_inactivacion,
               {datos_titular}
        FROM Base AS B
        {fuente_inactivacion}
        {titular}
    ), Clasificadas AS (
        SELECT *,
               CASE
                   {rangos_edad}
                   ELSE 0
               END AS rango_edad,
               YEAR(ultima_transaccion) AS anio,
               CONVERT(char(7), ultima_transaccion, 126) AS mes
        FROM Datos
    )
    SELECT
        CASE
            WHEN GROUPING(rango_edad) = 0 THEN 'rango_edad'
            WHEN GROUPING(sexo) = 0 THEN 'sexo'
            WHEN GROUPING(estado_civil) = 0 THEN 'estado_civil'
            WHEN GROUPING(socio) = 0 THEN 'socio'
            WHEN GROUPING(anio) = 0 THEN 'anio'
            WHEN GROUPING(mes) = 0 THEN 'mes_agencia'
            WHEN GROUPING(mes_apertura) = 0 THEN 'mes_apertura'
            WHEN GROUPING(id_agencia) = 0 THEN 'agencia'
            ELSE 'total'
        END AS dimension,
        rango_edad, sexo, estado_civil, socio, id_agencia, agencia, anio, mes, mes_apertura,
        COUNT_BIG(*) AS cuentas_brutas,
        COUNT_BIG(CASE WHEN saldo = 0 THEN 1 END) AS cuentas_cero,
        COUNT_BIG(CASE WHEN saldo > 0 THEN 1 END) AS cuentas_positivas,
        COALESCE(SUM(CASE WHEN saldo > 0 THEN saldo END), 0) AS saldo_total,
        MAX(CASE WHEN saldo > 0 THEN saldo END) AS saldo_maximo,
        MIN(CASE WHEN saldo > 0 THEN saldo END) AS saldo_minimo,
        COUNT_BIG(dias) AS cuentas_con_dias,
        AVG(CAST(dias AS decimal(18, 4))) AS dias_promedio,
        MAX(dias) AS dias_maximo,
        MIN(dias) AS dias_minimo,
        COUNT_BIG(dias_inactivacion) AS cuentas_con_inactivacion,
        AVG(CAST(dias_inactivacion AS decimal(18, 4))) AS inactivacion_promedio,
        MAX(dias_inactivacion) AS inactivacion_maximo,
        MIN(dias_inactivacion) AS inactivacion_minimo
    FROM Clasificadas
    GROUP BY GROUPING SETS (
        (), (rango_edad), (sexo), (estado_civil), (socio),
        (id_agencia, agencia), (anio), (mes, id_agencia, agencia), (mes_apertura)
    )
    HAVING GROUPING_ID(
        rango_edad, sexo, estado_civil, socio, id_agencia, agencia, anio, mes, mes_apertura
    ) = 511
        OR (:incluir_analisis = 1 AND COUNT_BIG(CASE WHEN saldo > 0 THEN 1 END) > 0)
"""


class SqlIndicadoresInactividadRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_indicadores(
        self, *, ids_agencia: list[int], fecha_sistema: date,
        incluir_analisis: bool,
    ) -> Sequence[Mapping[str, Any]]:
        historial = ""
        fuente_inactivacion = ""
        dias_inactivacion = "CAST(NULL AS int)"
        if incluir_analisis:
            historial = secuencia_inactivacion("CuentasCandidatas") + ","
            fuente_inactivacion = """
                LEFT JOIN UltimaInactivacion AS UI ON UI.NUMEROCUENTA = B.NUMERO AND B.saldo > 0
            """
            dias_inactivacion = "DATEDIFF(day, UI.FECHA, :fecha_sistema)"
        consulta = text(_CONSULTA.format(
            tablas_cuenta=TABLAS_CUENTA_BASE,
            historial=historial,
            fuente_inactivacion=fuente_inactivacion,
            dias_inactivacion=dias_inactivacion,
            saldos_cuenta=SALDOS_POR_CUENTA,
            datos_titular=_DATOS_TITULAR,
            rangos_edad=_RANGOS_EDAD_SQL,
            titular=_TITULAR_PRINCIPAL,
        )).bindparams(AGENCIA_EXPANDIBLE)
        params = {
            "ids_agencia": ids_agencia, "fecha_sistema": fecha_sistema,
            "incluir_analisis": int(incluir_analisis),
        }
        return self.db.execute(consulta, params).mappings().all()

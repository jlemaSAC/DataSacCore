from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


class CorteAhorroVistaNoDisponible(ValueError):
    pass


class SqlResumenAhorroVistaRepository:
    """Universo del analítico por tipo de ahorro, sin transacciones ni préstamos."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_saldos_diarios(
        self, fecha_inicio: date, fecha_fin: date, agencias: list[str],
        es_programado: bool = False,
    ) -> list[dict[str, Any]]:
        """Saldos por cierre diario en bloque; el servicio reutiliza el corte final."""
        if fecha_fin < fecha_inicio:
            return []
        cortes = self.db.execute(text("""
            SELECT CAST(C.FECHASISTEMA AS date) AS fecha, C.FECHACIERREVISTA AS cierre
            FROM GENERAL.EMPRESA_CIERREHISTORICO AS C
            WHERE C.FECHASISTEMA >= :fecha_inicio AND C.FECHASISTEMA < :hasta
              AND C.FECHACIERREVISTA IS NOT NULL
            ORDER BY C.FECHASISTEMA
        """), {
            "fecha_inicio": fecha_inicio, "hasta": fecha_fin + timedelta(days=1),
        }).mappings().all()
        if not cortes:
            return []
        # AS OF permite buscar por cada instante exacto del cierre. Una sola
        # ejecución, con una rama por día (el contrato limita el rango a un mes).
        # Evitar cruzar todas las versiones temporales de cuentas e ítems entre sí.
        parametros: dict[str, Any] = {"es_programado": es_programado}
        consultas = []
        filtro_agencias = (
            "AND UPPER(COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), N''), N'SIN DATOS')) IN :agencias"
            if agencias else ""
        )
        for indice, corte in enumerate(cortes):
            parametros[f"fecha_{indice}"] = corte["fecha"]
            parametros[f"cierre_{indice}"] = corte["cierre"]
            consultas.append(f"""
                SELECT CAST(:fecha_{indice} AS date) AS fecha,
                    COALESCE(SUM(CONVERT(decimal(18,2), S.saldo)), 0) AS saldo
                FROM (
                    SELECT CU.NUMERO, SUM(CI.SALDO) AS saldo
                    FROM AHORROS.CUENTA FOR SYSTEM_TIME AS OF :cierre_{indice} AS CU
                    INNER JOIN AHORROS.TIPO_CUENTA AS TC
                        ON TC.CODIGO = CU.CODIGOTIPOCUENTA AND TC.ESPROGRAMADO = :es_programado
                    INNER JOIN AHORROS.CUENTA_ITEMSALDO
                        FOR SYSTEM_TIME AS OF :cierre_{indice} AS CI
                        ON CI.NUMEROCUENTA = CU.NUMERO
                    INNER JOIN AHORROS.ITEMSALDO AS I ON I.ID = CI.IDITEM AND I.SUMASALDO = 1
                    LEFT JOIN GENERAL.AGENCIA AS A ON A.ID = CU.IDAGENCIA
                    WHERE CU.CODIGOESTADO IN (N'A', N'I', N'B')
                      AND CU.CODIGOTIPOCUENTA <> N'001'
                      AND EXISTS (
                        SELECT 1 FROM AHORROS.CUENTA_CLIENTE AS CC
                        INNER JOIN CLIENTES.CLIENTE AS CL ON CL.ID = CC.IDCLIENTE
                        INNER JOIN SUJETO.PERSONA AS P ON P.ID = CL.IDPERSONA
                        WHERE CC.NUMEROCUENTA = CU.NUMERO AND CC.PRINCIPAL = 1
                      )
                      {filtro_agencias}
                    GROUP BY CU.NUMERO
                ) AS S
            """)
        query = text(" UNION ALL ".join(consultas) + " ORDER BY fecha")
        if agencias:
            query = query.bindparams(bindparam("agencias", expanding=True))
            parametros["agencias"] = agencias
        return [dict(f) for f in self.db.execute(query, parametros).mappings().all()]

    def obtener_corte(self, fecha: date, es_programado: bool = False) -> tuple[date, list[dict[str, Any]]]:
        corte = self.db.execute(text("""
            WITH Sistema AS (
                SELECT MIN(CS.FECHASISTEMA) AS fecha_sistema
                FROM GENERAL.CALENDARIO_SISTEMA AS CS
                WHERE CS.FECHASISTEMA > (
                    SELECT MAX(C.FECHASISTEMA)
                    FROM GENERAL.CALENDARIO_SISTEMA AS C WHERE C.SECERRO = 1
                )
            )
            SELECT TOP (1) CAST(CS.FECHASISTEMA AS date) AS fecha_corte,
                CAST(S.fecha_sistema AS date) AS fecha_sistema, C.FECHACIERREVISTA AS cierre
            FROM GENERAL.CALENDARIO_SISTEMA AS CS
            CROSS JOIN Sistema AS S
            LEFT JOIN GENERAL.EMPRESA_CIERREHISTORICO AS C
                ON C.FECHASISTEMA = CS.FECHASISTEMA
            WHERE CS.FECHASISTEMA >= :mes
              AND CS.FECHASISTEMA < :hasta
              AND :fecha <= CAST(S.fecha_sistema AS date)
            ORDER BY CS.FECHASISTEMA DESC
        """), {"mes": fecha.replace(day=1), "hasta": fecha + timedelta(days=1), "fecha": fecha}).mappings().first()
        if corte is None:
            raise CorteAhorroVistaNoDisponible("No existe un corte operativo para la fecha solicitada.")
        fecha_corte = corte["fecha_corte"]
        if isinstance(fecha_corte, datetime):
            fecha_corte = fecha_corte.date()
        historico = fecha_corte != corte["fecha_sistema"]
        if historico and corte["cierre"] is None:
            raise CorteAhorroVistaNoDisponible("Falta el cierre histórico de ahorros a la vista para la fecha solicitada.")
        temporal = "FOR SYSTEM_TIME AS OF :cierre" if historico else ""
        # La cláusula temporal solo proviene de estas constantes; valores parametrizados.
        query = f"""
            WITH Cuentas AS (
                SELECT CU.NUMERO, CU.IDAGENCIA, CU.CODIGOUSUARIOOFICIAL,
                    CU.CODIGOESTADO, CU.CODIGOTIPOCUENTA
                FROM AHORROS.CUENTA {temporal} AS CU
                INNER JOIN AHORROS.TIPO_CUENTA AS TipoCuenta
                    ON TipoCuenta.CODIGO = CU.CODIGOTIPOCUENTA
                   AND TipoCuenta.ESPROGRAMADO = :es_programado
                WHERE CU.CODIGOESTADO IN (N'A', N'I', N'B')
                  AND CU.CODIGOTIPOCUENTA <> N'001'
                  AND EXISTS (
                    SELECT 1 FROM AHORROS.CUENTA_CLIENTE AS CC
                    INNER JOIN CLIENTES.CLIENTE AS CL ON CL.ID = CC.IDCLIENTE
                    INNER JOIN SUJETO.PERSONA AS P ON P.ID = CL.IDPERSONA
                    WHERE CC.NUMEROCUENTA = CU.NUMERO AND CC.PRINCIPAL = 1
                  )
            ), Saldos AS (
                SELECT CI.NUMEROCUENTA, SUM(CI.SALDO) AS saldo
                FROM AHORROS.CUENTA_ITEMSALDO {temporal} AS CI
                INNER JOIN Cuentas AS CU ON CU.NUMERO = CI.NUMEROCUENTA
                INNER JOIN AHORROS.ITEMSALDO AS I ON I.ID = CI.IDITEM AND I.SUMASALDO = 1
                GROUP BY CI.NUMEROCUENTA
            ), Tasas AS (
                SELECT CI.NUMEROCUENTA, MAX(T.TASA) AS tasa
                FROM AHORROS.CUENTA_ITEMSALDO {temporal} AS CI
                INNER JOIN Saldos AS S ON S.NUMEROCUENTA = CI.NUMEROCUENTA
                INNER JOIN AHORROS.ITEMSALDO AS I ON I.ID = CI.IDITEM AND I.SUMASALDO = 1
                INNER JOIN AHORROS.ITEMSALDO_TASA {temporal} AS T
                    ON T.IDITEM = CI.IDITEM AND T.ACTIVO = 1
                    AND S.saldo >= T.SALDOINICIAL AND S.saldo <= T.SALDOFINAL
                GROUP BY CI.NUMEROCUENTA
            ), Hechos AS (
                SELECT COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), N''), N'SIN DATOS') AS agencia,
                    COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), N''), CU.CODIGOUSUARIOOFICIAL, N'SIN DATOS') AS asesor,
                    COALESCE(NULLIF(LTRIM(RTRIM(E.NOMBRE)), N''), N'SIN DATOS') AS estado,
                    COALESCE(NULLIF(LTRIM(RTRIM(TC.NOMBRE)), N''), N'SIN DATOS') AS producto_ahorro,
                    CONVERT(decimal(18,2), S.saldo) AS saldo,
                    CONVERT(decimal(18,2), COALESCE(T.tasa, 0)) AS tasa_decimal
                FROM Cuentas AS CU
                INNER JOIN Saldos AS S ON S.NUMEROCUENTA = CU.NUMERO
                INNER JOIN AHORROS.TIPO_CUENTA AS TC ON TC.CODIGO = CU.CODIGOTIPOCUENTA
                LEFT JOIN Tasas AS T ON T.NUMEROCUENTA = CU.NUMERO
                LEFT JOIN GENERAL.AGENCIA AS A ON A.ID = CU.IDAGENCIA
                LEFT JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = CU.CODIGOUSUARIOOFICIAL
                LEFT JOIN AHORROS.ESTADO_CUENTA AS E ON E.CODIGO = CU.CODIGOESTADO
            )
            SELECT agencia, asesor, estado, producto_ahorro, tasa_decimal,
                SUM(saldo) AS saldo, COUNT_BIG(*) AS numero_cuentas
            FROM Hechos
            GROUP BY agencia, asesor, estado, producto_ahorro, tasa_decimal
        """
        filas = self.db.execute(text(query), {"cierre": corte["cierre"], "es_programado": es_programado}).mappings().all()
        return fecha_corte, [dict(fila) for fila in filas]

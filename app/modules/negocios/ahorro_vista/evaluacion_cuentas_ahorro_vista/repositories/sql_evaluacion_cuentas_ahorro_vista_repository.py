from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class CorteEvaluacionAhorroVista:
    fecha: date
    filas: list[dict[str, Any]]


class SqlEvaluacionCuentasAhorroVistaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_corte(
        self, *, fecha: date, fecha_sistema: date, id_agencia: int,
    ) -> CorteEvaluacionAhorroVista | None:
        corte = self.db.execute(text("""
            SELECT TOP (1) CAST(CS.FECHASISTEMA AS date) AS fecha,
                CS.SECERRO AS cerrado, C.FECHACIERREVISTA AS cierre
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
        temporal = "" if en_linea else "FOR SYSTEM_TIME AS OF :cierre"
        filtro_agencia = "AND CU.IDAGENCIA = :id_agencia" if id_agencia else ""
        # Solo se interpolan cláusulas constantes. Agregar por cuenta antes de
        # unir tasas evita multiplicar saldos y conteos por los ítems y rangos.
        filas = self.db.execute(text(f"""
            WITH Cuentas AS (
                SELECT CU.NUMERO, CU.IDAGENCIA, CU.CODIGOUSUARIOOFICIAL,
                    CU.CODIGOTIPOCUENTA
                FROM AHORROS.CUENTA {temporal} AS CU
                INNER JOIN AHORROS.TIPO_CUENTA AS TC
                    ON TC.CODIGO = CU.CODIGOTIPOCUENTA AND TC.ESPROGRAMADO = 0
                WHERE CU.CODIGOESTADO IN (N'A', N'I', N'B')
                  AND CU.CODIGOTIPOCUENTA <> N'001'
                  {filtro_agencia}
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
            ), Agrupados AS (
                SELECT CU.IDAGENCIA AS id_agencia,
                    COALESCE(NULLIF(LTRIM(RTRIM(CU.CODIGOUSUARIOOFICIAL)), N''), N'SIN USUARIO') AS codigo_usuario,
                    CU.CODIGOTIPOCUENTA AS codigo_producto,
                    SUM(CONVERT(decimal(18,2), S.saldo)) AS saldo,
                    COUNT_BIG(*) AS cuentas, SUM(COALESCE(T.tasa, 0)) AS suma_tasas
                FROM Cuentas AS CU
                INNER JOIN Saldos AS S ON S.NUMEROCUENTA = CU.NUMERO
                LEFT JOIN Tasas AS T ON T.NUMEROCUENTA = CU.NUMERO
                GROUP BY CU.IDAGENCIA,
                    COALESCE(NULLIF(LTRIM(RTRIM(CU.CODIGOUSUARIOOFICIAL)), N''), N'SIN USUARIO'),
                    CU.CODIGOTIPOCUENTA
            )
            SELECT X.*,
                COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), N''), N'SIN AGENCIA') AS agencia,
                COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), N''), X.codigo_usuario) AS nombre,
                COALESCE(NULLIF(LTRIM(RTRIM(TC.NOMBRE)), N''), X.codigo_producto) AS producto_ahorro
            FROM Agrupados AS X
            LEFT JOIN GENERAL.AGENCIA AS A ON A.ID = X.id_agencia
            LEFT JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = X.codigo_usuario
            INNER JOIN AHORROS.TIPO_CUENTA AS TC ON TC.CODIGO = X.codigo_producto
            ORDER BY X.id_agencia, X.codigo_usuario, X.codigo_producto
        """), {"cierre": corte["cierre"], "id_agencia": id_agencia}).mappings().all()
        return CorteEvaluacionAhorroVista(fecha_real, [dict(fila) for fila in filas])

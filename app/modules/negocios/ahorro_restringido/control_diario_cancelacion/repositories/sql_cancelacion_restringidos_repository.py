from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class CorteCancelacionRestringidos:
    fecha: date
    filas: list[dict[str, Any]]


class SqlCancelacionRestringidosRepository:
    """Último cierre válido de cuentas programadas cerradas al corte seleccionado."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_corte(
        self, *, fecha_inicio: date, fecha_fin: date, id_agencia: int, fecha_sistema: date,
    ) -> CorteCancelacionRestringidos | None:
        corte = self.db.execute(text("""
            SELECT TOP (1) CAST(CS.FECHASISTEMA AS date) AS fecha,
                CS.SECERRO AS cerrado, C.FECHACIERREVISTA AS cierre
            FROM GENERAL.CALENDARIO_SISTEMA AS CS
            LEFT JOIN GENERAL.EMPRESA_CIERREHISTORICO AS C
                ON C.FECHASISTEMA = CS.FECHASISTEMA
            WHERE CS.FECHASISTEMA >= :inicio_mes AND CS.FECHASISTEMA < :hasta
            ORDER BY CS.FECHASISTEMA DESC
        """), {
            "inicio_mes": fecha_fin.replace(day=1), "hasta": fecha_fin + timedelta(days=1),
        }).mappings().first()
        if corte is None:
            return None
        fecha = corte["fecha"]
        if isinstance(fecha, datetime):
            fecha = fecha.date()
        en_linea = fecha == fecha_sistema and not corte["cerrado"]
        if not en_linea and corte["cierre"] is None:
            return None
        temporal = "" if en_linea else "FOR SYSTEM_TIME AS OF :cierre"
        # No filtrar CM.CODIGOESTADOCUENTA: el movimiento conserva el estado A previo
        # al cierre. Tampoco sumar todos los débitos: los intereses internos tienen
        # SUMASALDO=0 y duplicarían parte de la salida del saldo de la cuenta.
        filas = self.db.execute(text(f"""
            WITH Cuentas AS (
                SELECT CU.NUMERO, CU.IDAGENCIA, CU.CODIGOTIPOCUENTA,
                    COALESCE(NULLIF(LTRIM(RTRIM(CU.CODIGOUSUARIOOFICIAL)), N''), N'SIN USUARIO') AS codigo_usuario
                FROM AHORROS.CUENTA {temporal} AS CU
                INNER JOIN AHORROS.TIPO_CUENTA AS TC ON TC.CODIGO = CU.CODIGOTIPOCUENTA
                WHERE TC.ESPROGRAMADO = :es_programado AND CU.CODIGOESTADO = :estado_cerrado
                  AND (:id_agencia = 0 OR CU.IDAGENCIA = :id_agencia)
            ), Salidas AS (
                SELECT MT.ID AS id_movimiento, CM.NUMEROCUENTA,
                    CAST(MT.FECHASISTEMA AS date) AS fecha_cancelacion,
                    SUM(IM.VALOR) AS monto
                FROM FINANCIERO.MOVIMIENTO_TRANSACCION AS MT
                INNER JOIN FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE AS MD
                    ON MD.IDMOVIMIENTOTRANSACCION = MT.ID
                INNER JOIN AHORROS.CUENTA_MOVIMIENTOTRANSACCIONDETALLE AS CM
                    ON CM.IDMOVIMIENTOTRANSACCIONDETALLE = MD.ID
                INNER JOIN Cuentas AS CU ON CU.NUMERO = CM.NUMEROCUENTA
                INNER JOIN AHORROS.CUENTA_ITEMSALDO_MOVIMIENTOTRANSACCIONDETALLE AS IM
                    ON IM.IDMOVIMIENTOTRANSACCIONDETALLE = MD.ID
                INNER JOIN AHORROS.CUENTA_ITEMSALDO {temporal} AS CI
                    ON CI.ID = IM.IDCUENTAITEMSALDO AND CI.NUMEROCUENTA = CM.NUMEROCUENTA
                INNER JOIN AHORROS.ITEMSALDO AS I ON I.ID = CI.IDITEM AND I.SUMASALDO = 1
                WHERE MT.IDTRANSACCION = :transaccion_cierre AND MD.DEBITO = 1
                  AND MT.FECHASISTEMA >= :fecha_inicio AND MT.FECHASISTEMA < :corte_exclusivo
                  AND MT.ESREVERSO = 0
                  AND NOT EXISTS (
                    SELECT 1 FROM FINANCIERO.MOVIMIENTO_TRANSACCION_REVERSO AS R
                    INNER JOIN FINANCIERO.MOVIMIENTO_TRANSACCION AS MR ON MR.ID = R.IDMOVIMIENTOREVERSO
                    WHERE R.IDMOVIMIENTO = MT.ID AND MR.FECHASISTEMA < :corte_exclusivo
                  )
                GROUP BY MT.ID, CM.NUMEROCUENTA, CAST(MT.FECHASISTEMA AS date)
                HAVING SUM(IM.VALOR) > 0
            ), Ultimos AS (
                SELECT S.*, ROW_NUMBER() OVER (
                    PARTITION BY S.NUMEROCUENTA ORDER BY S.fecha_cancelacion DESC, S.id_movimiento DESC
                ) AS orden FROM Salidas AS S
            )
            SELECT S.id_movimiento, S.NUMEROCUENTA AS numero_cuenta, S.fecha_cancelacion, S.monto,
                CU.codigo_usuario, CU.IDAGENCIA AS id_agencia, CU.CODIGOTIPOCUENTA AS codigo_producto,
                COALESCE(NULLIF(LTRIM(RTRIM(TC.NOMBRE)), N''), CU.CODIGOTIPOCUENTA) AS producto_ahorro,
                COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), N''), N'SIN AGENCIA') AS agencia,
                COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), N''), CU.codigo_usuario) AS nombre_asesor,
                COALESCE(NULLIF(LTRIM(RTRIM(Cargo.nombre)), N''), N'SIN CARGO') AS cargo,
                CAST(Cliente.numero_cliente AS nvarchar(100)) AS numero_cliente, Cliente.nombre_cliente
            FROM Ultimos AS S
            INNER JOIN Cuentas AS CU ON CU.NUMERO = S.NUMEROCUENTA
            INNER JOIN AHORROS.TIPO_CUENTA AS TC ON TC.CODIGO = CU.CODIGOTIPOCUENTA
            LEFT JOIN GENERAL.AGENCIA AS A ON A.ID = CU.IDAGENCIA
            LEFT JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = CU.codigo_usuario
            OUTER APPLY (
                SELECT TOP (1) C.NOMBRE AS nombre
                FROM NOMINA.EMPLEADO_USUARIO AS EU
                INNER JOIN NOMINA.EMPLEADO AS E ON E.ID = EU.IDEMPLEADO
                INNER JOIN NOMINA.CARGO AS C ON C.ID = E.IDCARGO
                WHERE EU.CODIGOUSUARIO = CU.codigo_usuario ORDER BY E.FECHAPROCESO DESC, E.ID DESC
            ) AS Cargo
            CROSS APPLY (
                SELECT TOP (1) CL.NUMERO AS numero_cliente, P.NOMBRE AS nombre_cliente
                FROM AHORROS.CUENTA_CLIENTE AS CC
                INNER JOIN CLIENTES.CLIENTE AS CL ON CL.ID = CC.IDCLIENTE
                INNER JOIN SUJETO.PERSONA AS P ON P.ID = CL.IDPERSONA
                WHERE CC.NUMEROCUENTA = CU.NUMERO AND CC.PRINCIPAL = 1 ORDER BY CC.ID
            ) AS Cliente
            WHERE S.orden = 1
        """), {
            "cierre": corte["cierre"], "fecha_inicio": fecha_inicio,
            "corte_exclusivo": fecha + timedelta(days=1), "id_agencia": id_agencia,
            "es_programado": True, "estado_cerrado": "C", "transaccion_cierre": 30,
        }).mappings().all()
        return CorteCancelacionRestringidos(fecha, [dict(fila) for fila in filas])

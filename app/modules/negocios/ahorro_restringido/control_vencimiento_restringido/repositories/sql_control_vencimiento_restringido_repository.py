from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


_METADATA = """
    LEFT JOIN GENERAL.AGENCIA AS A ON A.ID = X.IDAGENCIA
    LEFT JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = X.codigo
    OUTER APPLY (
        SELECT TOP (1) C.NOMBRE AS nombre
        FROM NOMINA.EMPLEADO_USUARIO AS EU
        INNER JOIN NOMINA.EMPLEADO AS E ON E.ID = EU.IDEMPLEADO
        INNER JOIN NOMINA.CARGO AS C ON C.ID = E.IDCARGO
        WHERE EU.CODIGOUSUARIO = X.codigo
        ORDER BY E.FECHAPROCESO DESC, E.ID DESC
    ) AS Cargo
"""
_CARGO = "COALESCE(NULLIF(LTRIM(RTRIM(Cargo.nombre)), N''), N'SIN CARGO')"
_AGENCIA = "COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), N''), N'SIN AGENCIA')"
_ASESOR = "COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), N''), X.codigo)"


@dataclass(frozen=True)
class DetalleVencimientoRestringidoResultado:
    total_registros: int
    total_saldo: Decimal
    items: list[dict[str, Any]]


class SqlControlVencimientoRestringidoRepository:
    """Saldo actual de contratos activos; resumen y detalle comparten el universo."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _base(
        fecha_inicio: date, fecha_fin: date, id_agencia: int, codigo_usuario: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        filtros = "AND CU.IDAGENCIA = :id_agencia" if id_agencia else ""
        params: dict[str, Any] = {
            "fecha_inicio": fecha_inicio, "hasta_exclusivo": fecha_fin + timedelta(days=1),
            "id_agencia": id_agencia, "es_programado": True,
        }
        if codigo_usuario is not None:
            filtros += " AND COALESCE(NULLIF(LTRIM(RTRIM(CU.CODIGOUSUARIOOFICIAL)), N''), N'SIN USUARIO') = :codigo_usuario"
            params["codigo_usuario"] = codigo_usuario
        # Una cuenta aporta su saldo una sola vez, aun si existieran varios contratos activos.
        # Elegir el contrato antes del rango evita rescatar un vencimiento anterior.
        return f"""
            WITH Programaciones AS (
                SELECT CP.*, ROW_NUMBER() OVER (
                    PARTITION BY CP.NUMEROCUENTA ORDER BY CP.FECHAINICIO DESC, CP.ID DESC
                ) AS orden
                FROM AHORROS.CUENTA_PROGRAMADO AS CP
                WHERE CP.ACTIVO = 1
            ), Cuentas AS (
                SELECT CU.NUMERO, CU.IDAGENCIA, CU.CODIGOESTADO, CU.CODIGOTIPOCUENTA,
                    COALESCE(NULLIF(LTRIM(RTRIM(CU.CODIGOUSUARIOOFICIAL)), N''), N'SIN USUARIO') AS codigo,
                    CP.ID AS id_programacion, CP.FECHAVENCIMIENTO, CP.TASAINTERES AS tasa,
                    TC.NOMBRE AS producto_ahorro
                FROM AHORROS.CUENTA AS CU
                INNER JOIN AHORROS.TIPO_CUENTA AS TC ON TC.CODIGO = CU.CODIGOTIPOCUENTA
                INNER JOIN Programaciones AS CP ON CP.NUMEROCUENTA = CU.NUMERO AND CP.orden = 1
                WHERE TC.ESPROGRAMADO = :es_programado
                  AND CU.CODIGOESTADO IN (N'A', N'I', N'B')
                  AND CU.CODIGOTIPOCUENTA <> N'001'
                  AND CP.FECHAVENCIMIENTO >= :fecha_inicio
                  AND CP.FECHAVENCIMIENTO < :hasta_exclusivo
                  {filtros}
                  AND EXISTS (
                      SELECT 1 FROM AHORROS.CUENTA_CLIENTE AS CC
                      INNER JOIN CLIENTES.CLIENTE AS CL ON CL.ID = CC.IDCLIENTE
                      INNER JOIN SUJETO.PERSONA AS P ON P.ID = CL.IDPERSONA
                      WHERE CC.NUMEROCUENTA = CU.NUMERO AND CC.PRINCIPAL = 1
                  )
            ), Saldos AS (
                SELECT CI.NUMEROCUENTA, CONVERT(decimal(18,2), SUM(CI.SALDO)) AS saldo
                FROM AHORROS.CUENTA_ITEMSALDO AS CI
                INNER JOIN Cuentas AS CU ON CU.NUMERO = CI.NUMEROCUENTA
                INNER JOIN AHORROS.ITEMSALDO AS I ON I.ID = CI.IDITEM AND I.SUMASALDO = 1
                GROUP BY CI.NUMEROCUENTA
            ), Vencimientos AS (
                SELECT CU.*, COALESCE(S.saldo, 0) AS saldo
                FROM Cuentas AS CU
                LEFT JOIN Saldos AS S ON S.NUMEROCUENTA = CU.NUMERO
            )
        """, params

    def obtener_saldos(self, *, fecha_inicio: date, fecha_fin: date, id_agencia: int) -> list[dict[str, Any]]:
        base, params = self._base(fecha_inicio, fecha_fin, id_agencia)
        result = self.db.execute(text(base + f"""
            , Agrupados AS (
                SELECT IDAGENCIA, codigo, CODIGOTIPOCUENTA AS codigo_producto, producto_ahorro, SUM(saldo) AS saldo
                FROM Vencimientos GROUP BY IDAGENCIA, codigo, CODIGOTIPOCUENTA, producto_ahorro
            )
            SELECT X.*, {_AGENCIA} AS agencia, {_ASESOR} AS nombre, {_CARGO} AS cargo
            FROM Agrupados AS X
            {_METADATA}
            ORDER BY X.IDAGENCIA, X.codigo, X.codigo_producto
        """), params)
        return [dict(fila) for fila in result.mappings().all()]

    def obtener_detalle(
        self, *, fecha_inicio: date, fecha_fin: date, id_agencia: int,
        codigo_usuario: str | None, productos: list[str], pagina: int, tamano_pagina: int,
        sin_paginacion: bool = False,
    ) -> DetalleVencimientoRestringidoResultado:
        base, params = self._base(fecha_inicio, fecha_fin, id_agencia, codigo_usuario)
        filtro_productos = ""
        if productos:
            claves = [f"producto_{i}" for i in range(len(productos))]
            filtro_productos = f"WHERE X.CODIGOTIPOCUENTA IN ({', '.join(':' + clave for clave in claves)})"
            params.update(zip(claves, productos))
        alcance = base + f"""
            , Alcance AS (
                SELECT X.*, {_AGENCIA} AS agencia, {_ASESOR} AS asesor
                FROM Vencimientos AS X
                {_METADATA}
                {filtro_productos}
            )
        """
        totales = self.db.execute(text(alcance + """
            SELECT COUNT(*) AS total_registros, COALESCE(SUM(saldo), 0) AS total_saldo
            FROM Alcance
        """), params).mappings().first()
        total = int(totales["total_registros"])
        offset = 0 if sin_paginacion else (pagina - 1) * tamano_pagina
        items = []
        if offset < total:
            paginacion = "" if sin_paginacion else """
                ORDER BY X.agencia, X.codigo, X.FECHAVENCIMIENTO, X.NUMERO, X.id_programacion
                OFFSET :offset ROWS FETCH NEXT :tamano_pagina ROWS ONLY
            """
            query_params = dict(params)
            if not sin_paginacion:
                query_params.update(offset=offset, tamano_pagina=tamano_pagina)
            result = self.db.execute(text(alcance + f"""
                , Pagina AS (SELECT X.* FROM Alcance AS X {paginacion})
                SELECT X.id_programacion, X.NUMERO AS numero_cuenta, X.producto_ahorro,
                    Cliente.numero_cliente, Cliente.nombre_cliente, X.agencia, X.asesor,
                    X.saldo AS saldo_actual, X.tasa, CAST(X.FECHAVENCIMIENTO AS date) AS fecha_vencimiento,
                    COALESCE(EC.NOMBRE, X.CODIGOESTADO) AS estado,
                    CONVERT(bit, CASE WHEN EXISTS (
                        SELECT 1 FROM COLOCACION.PRESTAMO_CLIENTE AS PC
                        INNER JOIN COLOCACION.PRESTAMO AS P ON P.ID = PC.IDPRESTAMO
                        WHERE PC.IDCLIENTE = Cliente.id_cliente AND PC.ACTIVO = 1
                          AND P.CODIGOESTADO <> N'C'
                    ) THEN 1 ELSE 0 END) AS tiene_prestamo
                FROM Pagina AS X
                CROSS APPLY (
                    SELECT TOP (1) CL.ID AS id_cliente, CL.NUMERO AS numero_cliente, P.NOMBRE AS nombre_cliente
                    FROM AHORROS.CUENTA_CLIENTE AS CC
                    INNER JOIN CLIENTES.CLIENTE AS CL ON CL.ID = CC.IDCLIENTE
                    INNER JOIN SUJETO.PERSONA AS P ON P.ID = CL.IDPERSONA
                    WHERE CC.NUMEROCUENTA = X.NUMERO AND CC.PRINCIPAL = 1
                    ORDER BY CC.ID
                ) AS Cliente
                LEFT JOIN AHORROS.ESTADO_CUENTA AS EC ON EC.CODIGO = X.CODIGOESTADO
            """), query_params)
            items = [dict(fila) for fila in result.mappings().all()]
        return DetalleVencimientoRestringidoResultado(
            total, Decimal(str(totales["total_saldo"])), items,
        )

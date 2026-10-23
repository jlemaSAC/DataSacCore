from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


# Se resuelve una sola referencia de cargo para no multiplicar depósitos.
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
_CARGO = "COALESCE(NULLIF(LTRIM(RTRIM(Cargo.nombre)), ''), 'SIN CARGO')"
_AGENCIA = "COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), ''), 'SIN AGENCIA')"
_CAPTADOR = "COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), ''), X.codigo)"


@dataclass(frozen=True)
class DetalleVencimientoResultado:
    total_registros: int
    total_monto: Decimal
    total_interes: Decimal
    items: list[dict[str, Any]]


class SqlControlVencimientoRepository:
    """Capital actual por vencimiento; resumen y detalle comparten el mismo universo."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _base(
        fecha_inicio: date, fecha_fin: date, id_agencia: int, codigo_usuario: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        filtros = "AND D.IDAGENCIA = :id_agencia" if id_agencia else ""
        params: dict[str, Any] = {
            "fecha_inicio": fecha_inicio, "hasta_exclusivo": fecha_fin + timedelta(days=1),
            "id_agencia": id_agencia,
        }
        if codigo_usuario is not None:
            filtros += " AND COALESCE(NULLIF(LTRIM(RTRIM(D.CODIGOUSUARIO)), ''), 'SIN USUARIO') = :codigo_usuario"
            params["codigo_usuario"] = codigo_usuario
        return f"""
            WITH Depositos AS (
                SELECT D.ID, D.IDAGENCIA,
                    COALESCE(NULLIF(LTRIM(RTRIM(D.CODIGOUSUARIO)), ''), 'SIN USUARIO') AS codigo,
                    D.MONTO, D.CODIGO AS numero_deposito, D.FECHAVENCIMIENTO,
                    D.CODIGOESTADODEPOSITO,
                    CONVERT(decimal(18,4), D.TASA + D.VARIACION_TASA) AS tasa_efectiva
                FROM INVERSION.DEPOSITO AS D
                WHERE D.FECHAVENCIMIENTO >= :fecha_inicio
                  AND D.FECHAVENCIMIENTO < :hasta_exclusivo
                  AND D.CODIGOESTADODEPOSITO IN ('A', 'E', 'V')
                  {filtros}
                  AND EXISTS (
                      SELECT 1 FROM INVERSION.DEPOSITO_CLIENTE AS DC
                      INNER JOIN CLIENTES.CLIENTE AS C ON C.ID = DC.IDCLIENTE
                      INNER JOIN SUJETO.PERSONA AS P ON P.ID = C.IDPERSONA
                      WHERE DC.IDDEPOSITO = D.ID AND DC.ESPRINCIPAL = 1 AND DC.ACTIVO = 1
                  )
            )
        """, params

    def obtener_saldos(self, *, fecha_inicio: date, fecha_fin: date, id_agencia: int) -> list[dict[str, Any]]:
        base, params = self._base(fecha_inicio, fecha_fin, id_agencia)
        result = self.db.execute(text(base + f"""
            , Agrupados AS (
                SELECT IDAGENCIA, codigo, SUM(MONTO) AS saldo
                FROM Depositos
                GROUP BY IDAGENCIA, codigo
            )
            SELECT X.*, {_AGENCIA} AS agencia, {_CAPTADOR} AS nombre, {_CARGO} AS cargo
            FROM Agrupados AS X
            {_METADATA}
            ORDER BY X.IDAGENCIA, X.codigo
        """), params)
        return [dict(fila) for fila in result.mappings().all()]

    def obtener_detalle(
        self, *, fecha_inicio: date, fecha_fin: date, id_agencia: int,
        codigo_usuario: str | None, cargos: list[str], pagina: int, tamano_pagina: int,
        sin_paginacion: bool = False,
    ) -> DetalleVencimientoResultado:
        base, params = self._base(fecha_inicio, fecha_fin, id_agencia, codigo_usuario)
        filtro_cargos = ""
        if cargos:
            claves = [f"cargo_{i}" for i in range(len(cargos))]
            filtro_cargos = f"WHERE {_CARGO} IN ({', '.join(':' + clave for clave in claves)})"
            params.update(zip(claves, cargos))
        alcance = base + f"""
            , Alcance AS (
                SELECT X.*, {_AGENCIA} AS agencia, {_CAPTADOR} AS captador
                FROM Depositos AS X
                {_METADATA}
                {filtro_cargos}
            ), Intereses AS (
                SELECT IP.IDDEPOSITO,
                    CONVERT(decimal(28,2), SUM(IP.CALCULADO)) AS interes_total
                FROM INVERSION.DEPOSITO_ITEMPLAZO AS IP
                INNER JOIN Alcance AS A ON A.ID = IP.IDDEPOSITO
                WHERE IP.IDITEMPLAZO = 2
                GROUP BY IP.IDDEPOSITO
            )
        """
        # Los intereses se agregan por DPF; nunca se unen las cuotas sin agrupar.
        totales = self.db.execute(text(alcance + """
            SELECT COUNT(*) AS total_registros,
                COALESCE(SUM(X.MONTO), 0) AS total_monto,
                COALESCE(SUM(I.interes_total), 0) AS total_interes
            FROM Alcance AS X
            LEFT JOIN Intereses AS I ON I.IDDEPOSITO = X.ID
        """), params).mappings().first()
        total = int(totales["total_registros"])
        offset = 0 if sin_paginacion else (pagina - 1) * tamano_pagina
        items = []
        if offset < total:
            pagina_cte = """
                , Pagina AS (
                    SELECT X.* FROM Alcance AS X
                )
            """ if sin_paginacion else """
                , Pagina AS (
                    SELECT X.* FROM Alcance AS X
                    ORDER BY X.agencia, X.codigo, X.FECHAVENCIMIENTO, X.ID
                    OFFSET :offset ROWS FETCH NEXT :tamano_pagina ROWS ONLY
                )
            """
            query_params = dict(params)
            if not sin_paginacion:
                query_params.update(offset=offset, tamano_pagina=tamano_pagina)
            result = self.db.execute(text(alcance + pagina_cte + """
                SELECT X.ID AS id_deposito, Cliente.numero_cliente, Cliente.nombre_cliente,
                    X.agencia, X.captador, X.numero_deposito, X.MONTO AS monto,
                    COALESCE(I.interes_total, 0) AS interes_total,
                    X.tasa_efectiva AS tasa_total, CAST(X.FECHAVENCIMIENTO AS date) AS fecha_vencimiento,
                    COALESCE(ED.NOMBRE, X.CODIGOESTADODEPOSITO) AS estado,
                    CONVERT(bit, CASE WHEN EXISTS (
                        SELECT 1 FROM COLOCACION.PRESTAMO_CLIENTE AS PC
                        INNER JOIN COLOCACION.PRESTAMO AS P ON P.ID = PC.IDPRESTAMO
                        WHERE PC.IDCLIENTE = Cliente.id_cliente AND PC.ACTIVO = 1
                          AND P.CODIGOESTADO <> 'C'
                    ) THEN 1 ELSE 0 END) AS tiene_prestamo
                FROM Pagina AS X
                CROSS APPLY (
                    SELECT TOP (1) C.ID AS id_cliente, C.NUMERO AS numero_cliente, P.NOMBRE AS nombre_cliente
                    FROM INVERSION.DEPOSITO_CLIENTE AS DC
                    INNER JOIN CLIENTES.CLIENTE AS C ON C.ID = DC.IDCLIENTE
                    INNER JOIN SUJETO.PERSONA AS P ON P.ID = C.IDPERSONA
                    WHERE DC.IDDEPOSITO = X.ID AND DC.ESPRINCIPAL = 1 AND DC.ACTIVO = 1
                    ORDER BY DC.ID
                ) AS Cliente
                LEFT JOIN Intereses AS I ON I.IDDEPOSITO = X.ID
                LEFT JOIN INVERSION.ESTADO_DEPOSITO AS ED ON ED.CODIGO = X.CODIGOESTADODEPOSITO
                ORDER BY X.agencia, X.codigo, X.FECHAVENCIMIENTO, X.ID
            """), query_params)
            items = [dict(fila) for fila in result.mappings().all()]
        return DetalleVencimientoResultado(
            total, Decimal(str(totales["total_monto"])), Decimal(str(totales["total_interes"])), items,
        )

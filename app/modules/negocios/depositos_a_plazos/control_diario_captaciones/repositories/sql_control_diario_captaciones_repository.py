from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class CorteCaptaciones:
    fecha: date
    filas: list[dict[str, Any]]


@dataclass(frozen=True)
class _Corte:
    fecha: date
    cierre: datetime | None
    cierre_colocacion: datetime | None
    en_linea: bool


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
_AGENCIA = "COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), ''), 'SIN DATOS')"
_CAPTADOR = "COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), ''), X.codigo)"
_CARGO = "COALESCE(NULLIF(LTRIM(RTRIM(Cargo.nombre)), ''), 'SIN CARGO')"


class SqlControlDiarioCaptacionesRepository:
    """Depósitos creados en el rango, excluyendo los anulados al corte."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _obtener_corte(self, fecha_fin: date, fecha_sistema: date) -> _Corte | None:
        corte = self.db.execute(text("""
            SELECT TOP (1) CAST(CS.FECHASISTEMA AS date) AS fecha,
                C.FECHACIERREPLAZO AS cierre, C.FECHACIERRECOLOCACION AS cierre_colocacion
            FROM GENERAL.CALENDARIO_SISTEMA AS CS
            LEFT JOIN GENERAL.EMPRESA_CIERREHISTORICO AS C
                ON CAST(C.FECHASISTEMA AS date) = CAST(CS.FECHASISTEMA AS date)
            WHERE CS.FECHASISTEMA >= :inicio_mes
              AND CS.FECHASISTEMA < :hasta_exclusivo
            ORDER BY CS.FECHASISTEMA DESC
        """), {
            "inicio_mes": fecha_fin.replace(day=1),
            "hasta_exclusivo": fecha_fin + timedelta(days=1),
        }).mappings().first()
        if corte is None:
            return None
        fecha_real = corte["fecha"]
        if isinstance(fecha_real, datetime):
            fecha_real = fecha_real.date()
        en_linea = fecha_real == fecha_sistema
        if not en_linea and corte["cierre"] is None:
            return None

        return _Corte(fecha_real, corte["cierre"], corte.get("cierre_colocacion"), en_linea)

    @staticmethod
    def _base(corte: _Corte, fecha_inicio: date, fecha_fin: date, id_agencia: int) -> tuple[str, dict[str, Any]]:
        # Resumen y detalle comparten fuente, universo y clasificación de renovaciones.
        fuente = "INVERSION.DEPOSITO" if corte.en_linea else "INVERSION.DEPOSITO FOR SYSTEM_TIME AS OF :cierre"
        return f"""
            WITH Depositos AS (
                SELECT D.ID, D.IDAGENCIA, D.CODIGO AS numero_deposito,
                    D.FECHAVENCIMIENTO, D.CODIGOESTADODEPOSITO,
                    COALESCE(NULLIF(LTRIM(RTRIM(D.CODIGOUSUARIO)), ''), 'SIN USUARIO') AS codigo,
                    CAST(D.FECHACREACION AS date) AS fecha,
                    D.MONTO,
                    CONVERT(decimal(18,4), D.TASA + D.VARIACION_TASA) AS tasa_total,
                    CASE WHEN EXISTS (
                        SELECT 1 FROM INVERSION.DEPOSITO_RENOVACION AS R
                        WHERE R.IDDEPOSITODESTINO = D.ID
                          AND R.FECHA >= :inicio_mes AND R.FECHA < :corte_exclusivo
                    ) THEN 'RENOVADO' ELSE 'NUEVO' END AS condicion
                FROM {fuente} AS D
                WHERE D.FECHACREACION >= :fecha_inicio
                  AND D.FECHACREACION < :hasta_exclusivo
                  AND (D.CODIGOESTADODEPOSITO IS NULL OR D.CODIGOESTADODEPOSITO <> 'N')
                  AND (:id_agencia = 0 OR D.IDAGENCIA = :id_agencia)
            )
        """, {
            "cierre": corte.cierre, "id_agencia": id_agencia,
            "fecha_inicio": fecha_inicio, "hasta_exclusivo": fecha_fin + timedelta(days=1),
            "inicio_mes": corte.fecha.replace(day=1),
            "corte_exclusivo": corte.fecha + timedelta(days=1),
        }

    def obtener_diario(
        self, *, fecha_inicio: date, fecha_fin: date, fecha_sistema: date, id_agencia: int
    ) -> CorteCaptaciones | None:
        corte = self._obtener_corte(fecha_fin, fecha_sistema)
        if corte is None:
            return None
        base, params = self._base(corte, fecha_inicio, fecha_fin, id_agencia)
        filas = self.db.execute(text(base + f"""
            , Agrupados AS (
                SELECT IDAGENCIA, codigo, fecha, condicion, SUM(MONTO) AS monto
                FROM Depositos
                GROUP BY IDAGENCIA, codigo, fecha, condicion
            )
            SELECT X.*, {_AGENCIA} AS agencia, {_CAPTADOR} AS nombre, {_CARGO} AS cargo
            FROM Agrupados AS X
            {_METADATA}
            ORDER BY X.IDAGENCIA, X.codigo, X.fecha, X.condicion
        """), params).mappings().all()
        return CorteCaptaciones(corte.fecha, [dict(fila) for fila in filas])

    def obtener_detalle(
        self, *, fecha_inicio: date, fecha_fin: date, fecha_sistema: date, id_agencia: int,
        fecha: date | None, codigo_usuario: str | None, cargos: list[str], condicion: str,
    ) -> CorteCaptaciones | None:
        corte = self._obtener_corte(fecha_fin, fecha_sistema)
        if corte is None or (not corte.en_linea and corte.cierre_colocacion is None):
            return None
        base, params = self._base(corte, fecha_inicio, fecha_fin, id_agencia)
        filtros = []
        if fecha is not None:
            filtros.append("X.fecha = :fecha")
            params["fecha"] = fecha
        if codigo_usuario is not None:
            filtros.append("X.codigo = :codigo_usuario")
            params["codigo_usuario"] = codigo_usuario
        if condicion != "todas":
            filtros.append("X.condicion = :condicion")
            params["condicion"] = condicion.upper()
        if cargos:
            claves = [f"cargo_{i}" for i in range(len(cargos))]
            filtros.append(f"UPPER({_CARGO}) IN ({', '.join(':' + clave for clave in claves)})")
            params.update(zip(claves, cargos))
        where = "WHERE " + " AND ".join(filtros) if filtros else ""
        intereses = "INVERSION.DEPOSITO_ITEMPLAZO" if corte.en_linea else "INVERSION.DEPOSITO_ITEMPLAZO FOR SYSTEM_TIME AS OF :cierre"
        prestamos = "COLOCACION.PRESTAMO" if corte.en_linea else "COLOCACION.PRESTAMO FOR SYSTEM_TIME AS OF :cierre_colocacion"
        params["cierre_colocacion"] = corte.cierre_colocacion
        filas = self.db.execute(text(base + f"""
            , Alcance AS (
                SELECT X.*, {_AGENCIA} AS agencia, {_CAPTADOR} AS captador
                FROM Depositos AS X
                {_METADATA}
                {where}
            )
            SELECT X.ID AS id_deposito,
                COALESCE(CONVERT(nvarchar(100), Cliente.numero_cliente), 'SIN DATOS') AS numero_cliente,
                COALESCE(NULLIF(LTRIM(RTRIM(Cliente.nombre_cliente)), ''), 'SIN DATOS') AS nombre_cliente,
                X.agencia, X.captador, X.numero_deposito, X.MONTO AS monto,
                COALESCE(I.interes_total, 0) AS interes_total,
                X.tasa_total,
                CAST(X.FECHAVENCIMIENTO AS date) AS fecha_vencimiento,
                COALESCE(ED.NOMBRE, X.CODIGOESTADODEPOSITO) AS estado,
                CONVERT(bit, CASE WHEN Cliente.id_cliente IS NULL THEN NULL WHEN EXISTS (
                    SELECT 1 FROM COLOCACION.PRESTAMO_CLIENTE AS PC
                    INNER JOIN {prestamos} AS P ON P.ID = PC.IDPRESTAMO
                    WHERE PC.IDCLIENTE = Cliente.id_cliente AND PC.ACTIVO = 1
                      AND P.CODIGOESTADO <> 'C'
                ) THEN 1 ELSE 0 END) AS tiene_prestamo
            FROM Alcance AS X
            OUTER APPLY (
                SELECT TOP (1) C.ID AS id_cliente, C.NUMERO AS numero_cliente, P.NOMBRE AS nombre_cliente
                FROM INVERSION.DEPOSITO_CLIENTE AS DC
                INNER JOIN CLIENTES.CLIENTE AS C ON C.ID = DC.IDCLIENTE
                INNER JOIN SUJETO.PERSONA AS P ON P.ID = C.IDPERSONA
                WHERE DC.IDDEPOSITO = X.ID AND DC.ESPRINCIPAL = 1 AND DC.ACTIVO = 1
                ORDER BY DC.ID
            ) AS Cliente
            OUTER APPLY (
                SELECT SUM(IP.CALCULADO) AS interes_total
                FROM {intereses} AS IP
                WHERE IP.IDDEPOSITO = X.ID AND IP.IDITEMPLAZO = 2
            ) AS I
            LEFT JOIN INVERSION.ESTADO_DEPOSITO AS ED ON ED.CODIGO = X.CODIGOESTADODEPOSITO
            ORDER BY X.agencia, X.captador, X.fecha, X.ID
        """), params).mappings().all()
        return CorteCaptaciones(corte.fecha, [dict(fila) for fila in filas])

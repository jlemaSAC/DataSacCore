from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


class SqlCastigoRepository:
    """Completa el corte del día con el cálculo de DepositosMes del reporte SQL."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_depositos_mes(self, numeros: list[str], fecha: date) -> dict[str, Decimal]:
        if not numeros:
            return {}
        statement = text("""
            WITH PrestamosElegibles AS (
                SELECT P.NUMERO, PC.IDCLIENTE
                FROM COLOCACION.PRESTAMO AS P
                INNER JOIN COLOCACION.PRESTAMO_CLIENTE AS PC
                    ON PC.IDPRESTAMO = P.ID AND PC.ESPRINCIPAL = 1
                WHERE P.NUMERO IN :numeros
            ), ClientesElegibles AS (
                SELECT DISTINCT IDCLIENTE FROM PrestamosElegibles
            ), DepositosMes AS (
                SELECT CC.IDCLIENTE, SUM(MD.VALOR) AS TOTAL
                FROM FINANCIERO.MOVIMIENTO_TRANSACCION AS M
                INNER JOIN FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE AS MD
                    ON MD.IDMOVIMIENTOTRANSACCION = M.ID AND MD.DEBITO = 0
                INNER JOIN AHORROS.CUENTA_MOVIMIENTOTRANSACCIONDETALLE AS MDC
                    ON MDC.IDMOVIMIENTOTRANSACCIONDETALLE = MD.ID
                INNER JOIN AHORROS.CUENTA AS CM ON CM.NUMERO = MDC.NUMEROCUENTA
                INNER JOIN AHORROS.CUENTA_CLIENTE AS CC
                    ON CC.NUMEROCUENTA = CM.NUMERO AND CC.PRINCIPAL = 1
                INNER JOIN ClientesElegibles AS C ON C.IDCLIENTE = CC.IDCLIENTE
                WHERE M.FECHASISTEMA >= :inicio_mes AND M.FECHASISTEMA < :fin_exclusivo
                GROUP BY CC.IDCLIENTE
            )
            SELECT P.NUMERO AS NumeroPrestamo,
                   CAST(COALESCE(D.TOTAL, 0) AS INT) AS DepositosMes
            FROM PrestamosElegibles AS P
            LEFT JOIN DepositosMes AS D ON D.IDCLIENTE = P.IDCLIENTE
        """).bindparams(bindparam("numeros", expanding=True))
        # El reporte de origen almacena este acumulado en una columna TOTAL INT.
        resultado = {}
        for offset in range(0, len(numeros), 500):
            filas = self.db.execute(statement, {
                "numeros": numeros[offset:offset + 500],
                "inicio_mes": fecha.replace(day=1),
                "fin_exclusivo": fecha + timedelta(days=1),
            }).mappings()
            for fila in filas:
                resultado[str(fila["NumeroPrestamo"]).strip()] = Decimal(str(fila["DepositosMes"]))
        return resultado

    def obtener_movimientos(
        self, numeros: list[str], desde: date, hasta: date, pagina: int, tamano: int,
    ) -> tuple[list[dict], int, Decimal]:
        if not numeros:
            return [], 0, Decimal(0)
        # XML evita el límite de 2100 parámetros y funciona con compatibilidad SQL 110.
        from xml.etree.ElementTree import Element, SubElement, tostring

        raiz = Element("prestamos")
        for numero in sorted(set(numeros)):
            SubElement(raiz, "prestamo").text = numero
        params = {
            "prestamos_xml": tostring(raiz, encoding="unicode"),
            "desde": desde, "fin_exclusivo": hasta + timedelta(days=1),
            "offset": (pagina - 1) * tamano, "tamano": tamano,
        }
        cte = """
            WITH Solicitados AS (
                SELECT X.Item.value('(text())[1]', 'nvarchar(100)') AS Numero
                FROM (SELECT CAST(:prestamos_xml AS XML) AS Documento) AS D
                CROSS APPLY D.Documento.nodes('/prestamos/prestamo') AS X(Item)
            ), PrestamosElegibles AS (
                SELECT DISTINCT P.NUMERO, PC.IDCLIENTE
                FROM COLOCACION.PRESTAMO AS P
                INNER JOIN Solicitados AS S ON S.Numero = P.NUMERO
                INNER JOIN COLOCACION.PRESTAMO_CLIENTE AS PC
                    ON PC.IDPRESTAMO = P.ID AND PC.ESPRINCIPAL = 1
            ), ClientesElegibles AS (
                SELECT DISTINCT IDCLIENTE FROM PrestamosElegibles
            ), Movimientos AS (
                SELECT DISTINCT MD.ID AS IdDetalle, M.ID AS IdMovimiento,
                    M.FECHASISTEMA AS FechaSistema, M.FECHAPROCESO AS FechaProceso,
                    C.NUMERO AS Cliente, PER.NOMBRE AS NombreCliente,
                    CC.IDCLIENTE, MDC.NUMEROCUENTA AS NumeroCuenta,
                    COALESCE(M.DOCUMENTO, '') AS Documento,
                    COALESCE(T.NOMBRE, '') AS TipoTransaccion,
                    COALESCE(MD.DETALLE, '') AS Detalle,
                    MD.VALOR AS Valor, M.ESREVERSO AS EsReverso
                FROM FINANCIERO.MOVIMIENTO_TRANSACCION AS M
                INNER JOIN FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE AS MD
                    ON MD.IDMOVIMIENTOTRANSACCION = M.ID AND MD.DEBITO = 0
                INNER JOIN AHORROS.CUENTA_MOVIMIENTOTRANSACCIONDETALLE AS MDC
                    ON MDC.IDMOVIMIENTOTRANSACCIONDETALLE = MD.ID
                INNER JOIN AHORROS.CUENTA AS CM ON CM.NUMERO = MDC.NUMEROCUENTA
                INNER JOIN AHORROS.CUENTA_CLIENTE AS CC
                    ON CC.NUMEROCUENTA = CM.NUMERO AND CC.PRINCIPAL = 1
                INNER JOIN ClientesElegibles AS CE ON CE.IDCLIENTE = CC.IDCLIENTE
                INNER JOIN CLIENTES.CLIENTE AS C ON C.ID = CC.IDCLIENTE
                INNER JOIN SUJETO.PERSONA AS PER ON PER.ID = C.IDPERSONA
                LEFT JOIN FINANCIERO.TRANSACCION AS T ON T.ID = M.IDTRANSACCION
                WHERE M.FECHASISTEMA >= :desde AND M.FECHASISTEMA < :fin_exclusivo
            )
        """
        resumen = self.db.execute(text(cte + """
            SELECT COUNT(*) AS Cantidad, COALESCE(SUM(Valor), 0) AS Total
            FROM Movimientos
        """), params).mappings().one()
        filas = self.db.execute(text(cte + """
            SELECT M.IdDetalle, M.IdMovimiento, M.FechaSistema, M.FechaProceso,
                   M.Cliente, M.NombreCliente, M.NumeroCuenta, M.Documento,
                   M.TipoTransaccion, M.Detalle, M.Valor, M.EsReverso,
                   STUFF((SELECT DISTINCT ', ' + P.NUMERO
                          FROM PrestamosElegibles AS P WHERE P.IDCLIENTE = M.IDCLIENTE
                          FOR XML PATH(''), TYPE).value('.', 'nvarchar(max)'), 1, 2, '') AS PrestamosRelacionados
            FROM Movimientos AS M
            ORDER BY M.FechaSistema DESC, M.IdDetalle DESC
            OFFSET :offset ROWS FETCH NEXT :tamano ROWS ONLY
        """), params).mappings().all()
        return [dict(fila) for fila in filas], int(resumen["Cantidad"]), Decimal(str(resumen["Total"]))

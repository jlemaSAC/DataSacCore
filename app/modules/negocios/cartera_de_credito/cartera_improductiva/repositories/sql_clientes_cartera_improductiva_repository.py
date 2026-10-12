from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


class SqlClientesCarteraImproductivaRepository:
    """Lee datos del titular sin reemplazar los importes de los cortes Mongo."""

    batch_size = 1000

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_clientes(self, numeros: list[str]) -> dict[str, dict[str, str]]:
        statement = text("""
            SELECT P.NUMERO AS numero_prestamo,
                   Principal.numero_socio, Principal.nombre_cliente
            FROM COLOCACION.PRESTAMO AS P
            OUTER APPLY (
                SELECT TOP (1) C.NUMERO AS numero_socio, PER.NOMBRE AS nombre_cliente
                FROM COLOCACION.PRESTAMO_CLIENTE AS PC
                INNER JOIN CLIENTES.CLIENTE AS C ON C.ID = PC.IDCLIENTE
                INNER JOIN SUJETO.PERSONA AS PER ON PER.ID = C.IDPERSONA
                WHERE PC.IDPRESTAMO = P.ID AND PC.ACTIVO = 1
                ORDER BY PC.ESPRINCIPAL DESC, PC.ID ASC
            ) AS Principal
            WHERE P.NUMERO IN :numeros
        """).bindparams(bindparam("numeros", expanding=True))
        numeros = sorted(set(numeros))
        resultado: dict[str, dict[str, str]] = {}
        for inicio in range(0, len(numeros), self.batch_size):
            rows = self.db.execute(
                statement, {"numeros": numeros[inicio:inicio + self.batch_size]},
            ).mappings()
            for row in rows:
                resultado[str(row["numero_prestamo"]).strip()] = {
                    "NombreCliente": str(row["nombre_cliente"]).strip() if row["nombre_cliente"] else "",
                    "NumeroSocio": str(row["numero_socio"]) if row["numero_socio"] is not None else "",
                }
        return resultado

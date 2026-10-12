from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


class SqlClientesCarteraRepository:
    """Completa el cliente principal que no incluye el snapshot operativo."""

    batch_size = 1000

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_clientes(self, numeros_prestamo: list[str]) -> dict[str, str]:
        numeros = sorted(set(numeros_prestamo))
        statement = text("""
            SELECT P.NUMERO AS numero_prestamo, C.NUMERO AS numero_cliente
            FROM COLOCACION.PRESTAMO AS P
            INNER JOIN COLOCACION.PRESTAMO_CLIENTE AS PC
                ON PC.IDPRESTAMO = P.ID AND PC.ESPRINCIPAL = 1 AND PC.ACTIVO = 1
            INNER JOIN CLIENTES.CLIENTE AS C ON C.ID = PC.IDCLIENTE
            WHERE P.NUMERO IN :numeros
        """).bindparams(bindparam("numeros", expanding=True))
        resultado: dict[str, str] = {}
        for indice in range(0, len(numeros), self.batch_size):
            rows = self.db.execute(
                statement, {"numeros": numeros[indice:indice + self.batch_size]},
            ).mappings()
            for row in rows:
                resultado[str(row["numero_prestamo"]).strip()] = str(row["numero_cliente"])
        return resultado

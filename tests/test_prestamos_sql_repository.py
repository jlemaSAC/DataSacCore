from app.modules.prestamos.repositories.sql_universo_repository import SqlUniversoPrestamosRepository


class FakeResult:
    def mappings(self) -> "FakeResult":
        return self

    def all(self) -> list:
        return []


class FakeSession:
    def __init__(self) -> None:
        self.last_statement = None

    def execute(self, statement):
        self.last_statement = str(statement)
        return FakeResult()


def test_get_prestamos_actuales_no_agrega_order_by_en_cte_sin_limit() -> None:
    session = FakeSession()
    repository = SqlUniversoPrestamosRepository(session)

    repository.get_prestamos_actuales()

    prestamos_base_sql = session.last_statement.split("),", 1)[0]
    assert "SELECT \n" in prestamos_base_sql
    assert "ORDER BY P.ID" not in prestamos_base_sql
    assert "ORDER BY PB.IdPrestamo" in session.last_statement


def test_get_prestamos_actuales_agrega_top_y_order_by_en_cte_con_limit() -> None:
    session = FakeSession()
    repository = SqlUniversoPrestamosRepository(session)

    repository.get_prestamos_actuales(limit=100)

    prestamos_base_sql = session.last_statement.split("),", 1)[0]
    assert "SELECT TOP (100)" in prestamos_base_sql
    assert "ORDER BY P.ID" in prestamos_base_sql


def test_get_prestamos_actuales_calcula_exigibles_sobre_prestamos_base() -> None:
    session = FakeSession()
    repository = SqlUniversoPrestamosRepository(session)

    repository.get_prestamos_actuales(limit=100)

    assert "RubrosExigibles AS" in session.last_statement
    assert "ExigiblesClasificados AS" in session.last_statement
    assert "INNER JOIN PrestamosBase PB" in session.last_statement
    assert "PC.VALORALDIA" in session.last_statement
    assert "PC.VALORALDIAMASCUOTACTUAL" in session.last_statement
    assert "PC.VALORCANCELAPRESTAMO" in session.last_statement

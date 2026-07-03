from datetime import datetime

from app.modules.prestamos.constants import (
    SITUACION_CREDITICIA_ACTUAL_COLLECTION,
    SITUACION_CREDITICIA_HISTORICO_COLLECTION,
)
from app.modules.prestamos.mappers import format_fecha_corte, prestamo_snapshot_from_mongo
from app.modules.prestamos.repositories.mongo_universo_repository import MongoUniversoPrestamosRepository
from app.modules.prestamos.schemas import PrestamoUniverseRequest


class FakeMongoCollection:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = documents
        self.last_filter = None

    def find(self, query: dict) -> list[dict]:
        self.last_filter = query
        return self.documents


class FakeMongoDatabase:
    def __init__(self) -> None:
        self.collections = {
            SITUACION_CREDITICIA_ACTUAL_COLLECTION: FakeMongoCollection([]),
            SITUACION_CREDITICIA_HISTORICO_COLLECTION: FakeMongoCollection([]),
        }

    def __getitem__(self, name: str) -> FakeMongoCollection:
        return self.collections[name]


def test_format_fecha_corte_mantiene_yyyymmdd() -> None:
    assert format_fecha_corte(datetime(2026, 5, 31, 10, 30)) == "20260531"


def test_prestamo_snapshot_from_mongo_normaliza_aliases_historicos() -> None:
    snapshot = prestamo_snapshot_from_mongo(
        {
            "IdPrestamo": "10",
            "NumeroPrestamo": 123.0,
            "IdAgencia": "2",
            "Agencia": " centro ",
            "CodigoEstado": "C",
            "EstadoPrestamo": "cancelado",
            "ESDIFERIDO": "SI",
            "DiasVencidos": "17",
            "CodigoUsuario": " jperez ",
            "NombreCompleto": " Juan   Perez ",
            "ProvisionConsituida": "1.234,56",
            "SaldoCapital": "1000",
            "CapitalNoDevenga": "100",
            "CapitalVencido": "50",
            "Calificacion": " a-1 ",
            "Producto": " microcredito ",
            "TipoPrestamo": " ordinario ",
            "Provincia": " azuay ",
            "data_version": "20260618-1030",
        }
    )

    assert snapshot.id_prestamo == 10
    assert snapshot.numero_prestamo == "123"
    assert snapshot.agencia == "CENTRO"
    assert snapshot.es_cancelado is True
    assert snapshot.es_diferido is True
    assert snapshot.codigo_asesor == "JPEREZ"
    assert snapshot.provision_constituida == 1234.56
    assert snapshot.capital_vigente == 850
    assert snapshot.data_version == "20260618-1030"


def test_mongo_universo_repository_usa_coleccion_actual() -> None:
    mongo_db = FakeMongoDatabase()
    mongo_db.collections[SITUACION_CREDITICIA_ACTUAL_COLLECTION].documents = [
        {"NumeroPrestamo": "0001", "CodigoAsesor": "JPEREZ"}
    ]
    repository = MongoUniversoPrestamosRepository(mongo_db)

    snapshots = repository.get_actual_snapshots(PrestamoUniverseRequest(codigos_asesor=["jperez"]))

    assert len(snapshots) == 1
    assert snapshots[0].numero_prestamo == "0001"
    assert mongo_db.collections[SITUACION_CREDITICIA_ACTUAL_COLLECTION].last_filter["CodigoAsesor"] == {
        "$in": ["JPEREZ"]
    }


def test_mongo_universo_repository_usa_historico_con_fecha_corte() -> None:
    mongo_db = FakeMongoDatabase()
    mongo_db.collections[SITUACION_CREDITICIA_HISTORICO_COLLECTION].documents = [
        {"NumeroPrestamo": "0002", "CodigoUsuario": "MLOPEZ"}
    ]
    repository = MongoUniversoPrestamosRepository(mongo_db)

    snapshots = repository.get_historico_snapshots(
        PrestamoUniverseRequest(fecha_corte_anterior=datetime(2026, 5, 31), codigos_asesor=["mlopez"])
    )

    assert snapshots[0].codigo_asesor == "MLOPEZ"
    assert mongo_db.collections[SITUACION_CREDITICIA_HISTORICO_COLLECTION].last_filter["fecha_corte"] == "20260531"

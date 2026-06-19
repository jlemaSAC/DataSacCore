from datetime import datetime

from app.modules.prestamos.constants import (
    SITUACION_CREDITICIA_ACTUAL_COLLECTION,
    SITUACION_CREDITICIA_HISTORICO_COLLECTION,
)
from app.modules.prestamos.mappers import (
    format_fecha_corte,
    mongo_document_from_snapshot,
    prestamo_snapshot_from_mongo,
)
from app.modules.prestamos.repositories.mongo_universo_repository import MongoUniversoPrestamosRepository
from app.modules.prestamos.schemas import PrestamoUniverseRequest


class FakeBulkWriteResult:
    def __init__(self, *, upserted: int = 0, matched: int = 0, modified: int = 0) -> None:
        self.upserted_count = upserted
        self.matched_count = matched
        self.modified_count = modified


class FakeMongoCollection:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = documents
        self.last_filter = None
        self.last_projection = None
        self.created_indexes = []
        self.bulk_write_calls = 0
        self.last_operations = []

    def find(self, query: dict, projection: dict | None = None) -> list[dict]:
        self.last_filter = query
        self.last_projection = projection

        documents = self.documents
        if isinstance(query.get("IdPrestamo"), dict) and "$in" in query["IdPrestamo"]:
            ids = set(query["IdPrestamo"]["$in"])
            documents = [document for document in documents if document.get("IdPrestamo") in ids]

        if projection is None:
            return documents

        included_fields = {key for key, value in projection.items() if value}
        return [{key: value for key, value in document.items() if key in included_fields} for document in documents]

    def create_index(self, keys, **kwargs) -> str:
        self.created_indexes.append((keys, kwargs))
        return kwargs.get("name", "")

    def bulk_write(self, operations, ordered: bool) -> FakeBulkWriteResult:
        _ = ordered
        self.bulk_write_calls += 1
        self.last_operations = operations
        return FakeBulkWriteResult(upserted=len(operations))


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
    assert snapshot.id_agencia == 2
    assert snapshot.agencia == "CENTRO"
    assert snapshot.codigo_estado_prestamo == "C"
    assert snapshot.es_cancelado is True
    assert snapshot.es_diferido is True
    assert snapshot.dias_vencidos == 17
    assert snapshot.codigo_asesor == "JPEREZ"
    assert snapshot.nombre_asesor == "JUAN PEREZ"
    assert snapshot.provision_constituida == 1234.56
    assert snapshot.capital_vigente == 850
    assert snapshot.calificacion == "A-1"
    assert snapshot.producto == "MICROCREDITO"
    assert snapshot.tipo_prestamo == "ORDINARIO"
    assert snapshot.provincia == "AZUAY"
    assert snapshot.data_version == "20260618-1030"


def test_mongo_document_from_snapshot_incluye_diferido_y_dias_vencidos() -> None:
    snapshot = prestamo_snapshot_from_mongo(
        {
            "IdPrestamo": 10,
            "NumeroPrestamo": "0001",
            "EsDiferido": True,
            "DiasVencidos": 12,
        }
    )

    document = mongo_document_from_snapshot(
        snapshot,
        as_of=datetime(2026, 6, 18, 10, 30),
        data_version="20260618-103000",
    )

    assert document["EsDiferido"] is True
    assert document["DiasVencidos"] == 12
    assert document["SnapshotHash"]
    assert "NombreCompleto" not in document
    assert "CodigoUsuario" not in document


def test_mongo_document_from_snapshot_mantiene_hash_estable_sin_campos_tecnicos() -> None:
    snapshot = prestamo_snapshot_from_mongo(
        {
            "IdPrestamo": 10,
            "NumeroPrestamo": "0001",
            "SaldoCapital": 1000,
        }
    )

    first_document = mongo_document_from_snapshot(
        snapshot,
        as_of=datetime(2026, 6, 18, 10, 30),
        data_version="20260618-103000",
    )
    second_document = mongo_document_from_snapshot(
        snapshot,
        as_of=datetime(2026, 6, 19, 11, 45),
        data_version="20260619-114500",
    )
    changed_snapshot = prestamo_snapshot_from_mongo(
        {
            "IdPrestamo": 10,
            "NumeroPrestamo": "0001",
            "SaldoCapital": 1100,
        }
    )
    changed_document = mongo_document_from_snapshot(
        changed_snapshot,
        as_of=datetime(2026, 6, 19, 11, 45),
        data_version="20260619-114500",
    )

    assert first_document["SnapshotHash"] == second_document["SnapshotHash"]
    assert first_document["SnapshotHash"] != changed_document["SnapshotHash"]


def test_prestamo_snapshot_from_sql_calcula_provision_requerida_con_parametros() -> None:
    snapshot = prestamo_snapshot_from_mongo(
        {
            "IdPrestamo": 10,
            "NumeroPrestamo": "0001",
            "SaldoBaseProvision": 1000,
            "PorcentajeProvisionFuente": 2,
            "PorcentajeProvisionReglaFijo": 1.5,
            "PorcentajeProvisionMinimo": 1,
            "PorcentajeProvisionMaximo": 5,
            "EsPorcentajeFijo": True,
            "ProvisionAutomatica": 12,
            "ProvisionManual": 3,
            "ProvisionConstituida": 9,
        }
    )

    assert snapshot.provision_requerida == 15
    assert snapshot.provision_requerida_calculada == 15
    assert snapshot.provision_requerida_fuente == 15
    assert snapshot.provision_constituida == 9
    assert snapshot.porcentaje_provision_aplicado == 1.5
    assert snapshot.porcentaje_provision_fuente == 2
    assert snapshot.porcentaje_provision_minimo == 1
    assert snapshot.porcentaje_provision_maximo == 5
    assert snapshot.es_porcentaje_fijo is True
    assert snapshot.provision_diferencia_validacion == 0

    document = mongo_document_from_snapshot(
        snapshot,
        as_of=datetime(2026, 6, 18, 10, 30),
        data_version="20260618-103000",
    )

    assert document["ProvisionRequerida"] == 15
    assert document["ProvisionRequeridaFuente"] == 15
    assert document["ProvisionRequeridaCalculada"] == 15
    assert document["ProvisionConstituida"] == 9
    assert document["PorcentajeProvisionAplicado"] == 1.5
    assert document["ProvisionDiferenciaValidacion"] == 0


def test_prestamo_snapshot_from_sql_limita_porcentaje_no_fijo_a_minimo_y_maximo() -> None:
    snapshot = prestamo_snapshot_from_mongo(
        {
            "IdPrestamo": 10,
            "NumeroPrestamo": "0001",
            "SaldoBaseProvision": 1000,
            "PorcentajeProvisionFuente": 8,
            "PorcentajeProvisionMinimo": 1,
            "PorcentajeProvisionMaximo": 5,
            "EsPorcentajeFijo": False,
            "ProvisionAutomatica": 45,
            "ProvisionManual": 0,
        }
    )

    assert snapshot.porcentaje_provision_aplicado == 5
    assert snapshot.provision_requerida_calculada == 50
    assert snapshot.provision_requerida_fuente == 45
    assert snapshot.provision_requerida == 50
    assert snapshot.provision_diferencia_validacion == -5


def test_mongo_universo_repository_crea_indices_actual_una_sola_vez_por_instancia() -> None:
    mongo_db = FakeMongoDatabase()
    repository = MongoUniversoPrestamosRepository(mongo_db)

    repository.ensure_actual_indexes()
    repository.ensure_actual_indexes()

    created_indexes = mongo_db.collections[SITUACION_CREDITICIA_ACTUAL_COLLECTION].created_indexes
    assert len(created_indexes) == 11


def test_mongo_universo_repository_usa_coleccion_actual() -> None:
    mongo_db = FakeMongoDatabase()
    mongo_db.collections[SITUACION_CREDITICIA_ACTUAL_COLLECTION].documents = [
        {"NumeroPrestamo": "0001", "CodigoAsesor": "JPEREZ"}
    ]
    repository = MongoUniversoPrestamosRepository(mongo_db)

    snapshots = repository.get_actual_snapshots(PrestamoUniverseRequest(codigos_asesor=["jperez"]))

    assert len(snapshots) == 1
    assert snapshots[0].numero_prestamo == "0001"
    assert snapshots[0].codigo_asesor == "JPEREZ"
    assert mongo_db.collections[SITUACION_CREDITICIA_ACTUAL_COLLECTION].last_filter == {
        "CodigoAsesor": {"$in": ["JPEREZ"]},
        "$and": [
            {
                "$and": [
                    {"EstadoPrestamo": {"$nin": ["CANCELADO", "C"]}},
                    {"CodigoEstadoPrestamo": {"$ne": "C"}},
                    {"CodigoEstado": {"$ne": "C"}},
                ]
            },
        ]
    }


def test_mongo_universo_repository_usa_historico_con_fecha_corte_yyyymmdd() -> None:
    mongo_db = FakeMongoDatabase()
    mongo_db.collections[SITUACION_CREDITICIA_HISTORICO_COLLECTION].documents = [
        {"NumeroPrestamo": "0002", "CodigoUsuario": "MLOPEZ"}
    ]
    repository = MongoUniversoPrestamosRepository(mongo_db)

    snapshots = repository.get_historico_snapshots(
        PrestamoUniverseRequest(fecha_corte_anterior=datetime(2026, 5, 31), codigos_asesor=["mlopez"])
    )

    assert len(snapshots) == 1
    assert snapshots[0].numero_prestamo == "0002"
    assert snapshots[0].codigo_asesor == "MLOPEZ"
    assert mongo_db.collections[SITUACION_CREDITICIA_HISTORICO_COLLECTION].last_filter["fecha_corte"] == "20260531"


def test_mongo_universo_repository_omite_upsert_si_snapshot_hash_no_cambia() -> None:
    mongo_db = FakeMongoDatabase()
    snapshot = prestamo_snapshot_from_mongo(
        {
            "IdPrestamo": 10,
            "NumeroPrestamo": "0001",
            "SaldoCapital": 1000,
        }
    )
    existing_document = mongo_document_from_snapshot(
        snapshot,
        as_of=datetime(2026, 6, 18, 10, 30),
        data_version="20260618-103000",
    )
    mongo_db.collections[SITUACION_CREDITICIA_ACTUAL_COLLECTION].documents = [
        {
            "IdPrestamo": 10,
            "SnapshotHash": existing_document["SnapshotHash"],
        }
    ]
    repository = MongoUniversoPrestamosRepository(mongo_db)

    result = repository.upsert_actual_snapshots(
        [snapshot],
        as_of=datetime(2026, 6, 19, 9, 20),
        data_version="20260619-092000",
    )

    actual_collection = mongo_db.collections[SITUACION_CREDITICIA_ACTUAL_COLLECTION]
    assert result == {"upserted": 0, "matched": 0, "modified": 0, "unchanged": 1}
    assert actual_collection.bulk_write_calls == 0
    assert actual_collection.last_projection == {"IdPrestamo": 1, "SnapshotHash": 1, "_id": 0}

from datetime import date

from app.modules.analytic.recuperacion.recuperacion_historico.repositories.mongo_recuperacion_historico_repository import (
    MongoRecuperacionHistoricoRepository,
)
from app.modules.analytic.recuperacion.recuperacion_historico.schemas import (
    InputRecuperacionHistoricoRango,
)


class FakeCollection:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.pipeline = None
        self.allow_disk_use = None

    def aggregate(self, pipeline, allowDiskUse=False):
        self.pipeline = pipeline
        self.allow_disk_use = allowDiskUse
        return self.rows


class FakeDatabase:
    def __init__(self, collection: FakeCollection):
        self.collection = collection

    def __getitem__(self, name):
        assert name == "RecuperacionCrediticia"
        return self.collection


def test_mongo_consulta_todas_las_dimensiones() -> None:
    collection = FakeCollection([
        {
            "_id": {"periodo": "2026-01", "anio": 2026, "mes": 1, "tipo_cobro": "CAPITAL"},
            "total_recuperado": 123.45,
        }
    ])
    repository = MongoRecuperacionHistoricoRepository(FakeDatabase(collection))  # type: ignore[arg-type]

    resultado = repository.obtener_recuperaciones_agrupadas(
        InputRecuperacionHistoricoRango(
            fecha_desde=date(2026, 1, 1), fecha_hasta=date(2026, 1, 31)
        )
    )

    assert resultado[0].dimensiones["tipo_cobro"] == "CAPITAL"
    assert resultado[0].dimensiones["agencia"] == "SIN DATOS"
    assert resultado[0].total_recuperado == 123.45
    assert collection.allow_disk_use is True
    assert collection.pipeline[0] == {
        "$match": {"fecha_corte": {"$gte": "20260101", "$lte": "20260131"}}
    }
    lookups = [stage["$lookup"] for stage in collection.pipeline if "$lookup" in stage]
    assert [lookup["as"] for lookup in lookups] == [
        "situacion",
        "situacion_inicio",
        "situacion_fin",
    ]
    for lookup in lookups:
        condiciones = lookup["pipeline"][0]["$match"]["$expr"]["$and"]
        assert "$eq" in condiciones[1]
        assert not any("$sort" in stage for stage in lookup["pipeline"])


def test_mongo_agrupa_por_todos_los_campos() -> None:
    collection = FakeCollection()
    repository = MongoRecuperacionHistoricoRepository(FakeDatabase(collection))  # type: ignore[arg-type]

    repository.obtener_recuperaciones_agrupadas(
        InputRecuperacionHistoricoRango(
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
        )
    )

    lookups = [stage["$lookup"] for stage in collection.pipeline if "$lookup" in stage]
    assert [lookup["as"] for lookup in lookups] == [
        "situacion",
        "situacion_inicio",
        "situacion_fin",
    ]
    group_stage = next(stage["$group"] for stage in collection.pipeline if "$group" in stage)
    assert "agencia" in group_stage["_id"]
    assert "tipo_cobro" in group_stage["_id"]
    assert "estado_prestamo_inicio" in group_stage["_id"]
    assert "estado_prestamo_fin" in group_stage["_id"]


def test_entrada_no_admite_group_by() -> None:
    try:
        InputRecuperacionHistoricoRango(
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
            group_by=["tipo_cobro"],
        )
    except ValueError as exc:
        assert "Extra inputs" in str(exc)
    else:
        raise AssertionError("Se esperaba que group_by sea rechazado.")

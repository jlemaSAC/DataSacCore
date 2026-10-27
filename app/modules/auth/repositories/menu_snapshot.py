"""A bounded, in-memory working copy of the existing menu collections.

The working copy has no I/O. A completed change is persisted by one CAS write
of the enclosing MongoDB document, so failures cannot publish partial changes.
"""
from copy import deepcopy
from types import SimpleNamespace
from typing import Any, Mapping

from bson import ObjectId


class SnapshotCollection:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self.documents = documents

    @staticmethod
    def _matches(document: Mapping[str, Any], query: Mapping[str, Any]) -> bool:
        for field, expected in query.items():
            actual = document.get(field)
            if isinstance(expected, dict):
                for operator, values in expected.items():
                    if operator == "$in" and actual not in values:
                        return False
                    if operator == "$nin" and actual in values:
                        return False
                    if operator not in {"$in", "$nin"}:
                        raise ValueError(f"Operador no soportado: {operator}")
            elif actual != expected:
                return False
        return True

    def find(self, query: dict, projection: dict | None = None, **kwargs: Any) -> list[dict]:
        return [deepcopy(item) for item in self.documents if self._matches(item, query)]

    def find_one(self, query: dict, projection: dict | None = None, **kwargs: Any) -> dict | None:
        return next(iter(self.find(query, projection, **kwargs)), None)

    def insert_one(self, document: dict, **kwargs: Any) -> SimpleNamespace:
        item = deepcopy(document)
        item.setdefault("_id", ObjectId())
        self.documents.append(item)
        return SimpleNamespace(inserted_id=item["_id"])

    def update_one(self, query: dict, update: dict, upsert: bool = False, **kwargs: Any) -> None:
        item = next((item for item in self.documents if self._matches(item, query)), None)
        if item is None:
            if not upsert:
                return
            item = {key: deepcopy(value) for key, value in query.items() if not isinstance(value, dict)}
            item.setdefault("_id", ObjectId())
            item.update(deepcopy(update.get("$setOnInsert", {})))
            self.documents.append(item)
        item.update(deepcopy(update.get("$set", {})))

    def update_many(self, query: dict, update: dict, **kwargs: Any) -> None:
        for item in self.documents:
            if self._matches(item, query):
                item.update(deepcopy(update.get("$set", {})))

    def delete_one(self, query: dict, **kwargs: Any) -> None:
        for index, item in enumerate(self.documents):
            if self._matches(item, query):
                self.documents.pop(index)
                return

    def delete_many(self, query: dict, **kwargs: Any) -> None:
        self.documents[:] = [item for item in self.documents if not self._matches(item, query)]


class MenuSnapshot:
    names = ("menu", "permisos", "rol_permisos")

    def __init__(self, documents: dict[str, list[dict[str, Any]]]) -> None:
        self.collections = {name: SnapshotCollection(deepcopy(documents[name])) for name in self.names}

    def __getitem__(self, name: str) -> SnapshotCollection:
        return self.collections[name]

    def export(self) -> dict[str, list[dict[str, Any]]]:
        return {name: deepcopy(self.collections[name].documents) for name in self.names}

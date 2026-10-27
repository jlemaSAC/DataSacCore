"""Single-document persistence for DataSacWeb menu and access administration."""
import hashlib
from typing import Any, Callable, TypeVar

from bson import BSON, json_util
from fastapi import HTTPException
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.modules.auth.repositories.menu_snapshot import MenuSnapshot
from app.modules.auth.repositories.mongo_menu_repository import MongoMenuRepository
from app.modules.auth.schemas import MenuAdminChild, MenuChild

Result = TypeVar("Result")


class AtomicMenuRepository:
    state_collection_name = "menu_estado"
    state_id = "actual"
    # Leave headroom below MongoDB's 16 MiB BSON limit.
    max_state_bytes = 15 * 1024 * 1024

    def __init__(self, mongo_db: Database) -> None:
        self.mongo_db = mongo_db
        self.state_collection = mongo_db[self.state_collection_name]

    def _legacy(self) -> dict[str, list[dict[str, Any]]]:
        return {name: list(self.mongo_db[name].find({})) for name in MenuSnapshot.names}

    @staticmethod
    def _fingerprint(documents: dict[str, list[dict[str, Any]]]) -> str:
        normalized = {
            name: sorted(items, key=lambda item: str(item.get("_id")))
            for name, items in documents.items()
        }
        return hashlib.sha256(json_util.dumps(normalized, sort_keys=True).encode()).hexdigest()

    def _read_legacy_stable(self) -> tuple[dict[str, list[dict[str, Any]]], str]:
        previous = self._legacy()
        previous_hash = self._fingerprint(previous)
        for _ in range(3):
            current = self._legacy()
            digest = self._fingerprint(current)
            if digest == previous_hash:
                return current, digest
            previous, previous_hash = current, digest
        raise HTTPException(status_code=409, detail="Los menús están cambiando. Reintente la operación.")

    def _load(self) -> tuple[dict[str, Any] | None, MenuSnapshot, str]:
        state = self.state_collection.find_one({"_id": self.state_id})
        if state is None:
            documents, legacy_hash = self._read_legacy_stable()
        else:
            if state.get("schema_version") != 1:
                raise HTTPException(status_code=503, detail="Versión de almacenamiento de menús no compatible.")
            legacy_hash = state["legacy_hash"]
            if self._fingerprint(self._legacy()) != legacy_hash:
                raise HTTPException(
                    status_code=503,
                    detail="Se detectaron cambios externos en las colecciones antiguas. Es necesario reconciliarlos antes de continuar.",
                )
            documents = state["data"]
        return state, MenuSnapshot(documents), legacy_hash

    def _working(self, snapshot: MenuSnapshot) -> MongoMenuRepository:
        return MongoMenuRepository(snapshot)  # type: ignore[arg-type]

    def _read(self, operation: Callable[[MongoMenuRepository], Result]) -> Result:
        _, snapshot, _ = self._load()
        return operation(self._working(snapshot))

    def run_atomic(
        self, operation: Callable[[MongoMenuRepository], Result], *,
        require_transaction: bool = True,
    ) -> Result:
        state, snapshot, legacy_hash = self._load()
        before = snapshot.export()
        result = operation(self._working(snapshot))
        data = snapshot.export()
        if data == before:
            latest = self.state_collection.find_one({"_id": self.state_id})
            if (
                (state is None and latest is not None)
                or (state is not None and (latest is None or latest.get("revision") != state["revision"]))
                or self._fingerprint(self._legacy()) != legacy_hash
            ):
                raise HTTPException(status_code=409, detail="Los menús o permisos cambiaron. Recargue y revise los cambios.")
            return result
        if self._fingerprint(self._legacy()) != legacy_hash:
            raise HTTPException(status_code=409, detail="Las colecciones originales cambiaron. Recargue y revise los cambios.")
        new_state = {
            "_id": self.state_id,
            "schema_version": 1,
            "revision": (state["revision"] if state else 0) + 1,
            "legacy_hash": legacy_hash,
            "data": data,
        }
        if len(BSON.encode(new_state)) > self.max_state_bytes:
            raise HTTPException(status_code=413, detail="El estado de menús excede el tamaño permitido para una actualización atómica.")
        if state is None:
            try:
                self.state_collection.insert_one(new_state)
            except DuplicateKeyError as exc:
                raise HTTPException(status_code=409, detail="Otro administrador actualizó los permisos. Recargue y revise los cambios.") from exc
        else:
            result_write = self.state_collection.replace_one(
                {"_id": self.state_id, "revision": state["revision"]}, new_state,
            )
            if result_write.matched_count != 1:
                raise HTTPException(status_code=409, detail="Otro administrador actualizó los permisos. Recargue y revise los cambios.")
        return result

    def get_menu_by_role_codes(self, role_codes: list[str]) -> list[MenuChild]:
        return self._read(lambda repo: repo.get_menu_by_role_codes(role_codes))

    def get_complete_menu_tree(self, activo: bool | None = None) -> list[MenuAdminChild]:
        return self._read(lambda repo: repo.get_complete_menu_tree(activo))

    def get_menu_node(self, id_menu: str) -> MenuAdminChild:
        return self._read(lambda repo: repo.get_menu_node(id_menu))

import hashlib
import json
from typing import cast

from fastapi import HTTPException

from app.modules.auth.repositories.atomic_menu_repository import AtomicMenuRepository
from app.modules.auth.repositories.menu_snapshot import MenuSnapshot
from app.modules.auth.repositories.mongo_menu_repository import MongoMenuRepository
from app.modules.seguridad.permisos.schemas import AccessBatchRequest, AccessSnapshot


class MongoPermisoWorkingRepository(MongoMenuRepository):
    def _snapshot(self) -> AccessSnapshot:
        menu = self.get_complete_menu_tree()
        content = {
            "menu": [node.model_dump(mode="json") for node in menu],
            "relations": sorted(
                (str(row.get("_id")), str(row.get("rol_codigo")), str(row.get("permiso_codigo")), bool(row.get("activo")))
                for row in self.rol_permisos_collection.find({}, **self.query_options)
            ),
            "permissions": sorted(
                (str(row.get("codigo")), bool(row.get("activo")))
                for row in self.permisos_collection.find({}, **self.query_options)
            ),
        }
        version = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
        return AccessSnapshot(menu=menu, version=version)

    def _apply_batch(self, data: AccessBatchRequest) -> tuple[AccessSnapshot, int]:
        before = self._snapshot()
        if before.version != data.version:
            raise HTTPException(status_code=409, detail="Los accesos o menús cambiaron. Conserve su resumen, descarte y actualice antes de volver a guardar.")

        documents = list(self.menu_collection.find({}, **self.query_options))
        by_id = {str(document["_id"]): document for document in documents}
        for change in data.cambios:
            if change.menu_id not in by_id:
                raise HTTPException(status_code=404, detail="Menú no encontrado.")

        # A no-op must not migrate or rewrite the legacy data.
        roles_by_permission = self._roles_by_permission()
        has_changes = any(
            (change.rol_codigo in (
                set(by_id[change.menu_id]["roles_directos_codigos"])
                if by_id[change.menu_id].get("roles_directos_codigos") is not None
                else self._legacy_direct_roles(by_id[change.menu_id], documents, roles_by_permission)
            )) != change.conceder
            for change in data.cambios
        )
        if not has_changes:
            return before, 0

        # Freeze legacy grants before changing descendants or deriving parents.
        self._preserve_legacy_assignments()
        documents = list(self.menu_collection.find({}, **self.query_options))
        by_id = {str(document["_id"]): document for document in documents}
        changed_ids: set[str] = set()
        count = 0
        for change in data.cambios:
            document = by_id[change.menu_id]
            roles = set(document.get("roles_directos_codigos", []))
            if (change.rol_codigo in roles) == change.conceder:
                continue
            if change.conceder:
                roles.add(change.rol_codigo)
            else:
                roles.discard(change.rol_codigo)
            document["roles_directos_codigos"] = sorted(roles)
            changed_ids.add(change.menu_id)
            count += 1

        for menu_id in changed_ids:
            document = by_id[menu_id]
            self.menu_collection.update_one(
                {"_id": document["_id"]},
                {"$set": {"roles_directos_codigos": document["roles_directos_codigos"], "updated_at": self._now()}},
                **self.query_options,
            )
        if changed_ids:
            affected_permissions: set[str] = set()
            for menu_id in changed_ids:
                document = by_id[menu_id]
                while document:
                    affected_permissions.add(str(document["permiso_requerido"]))
                    parent = document.get("id_padre")
                    document = by_id.get(str(parent)) if parent else None
            self._sync_effective_role_permissions(only_permissions=affected_permissions)
        return self._snapshot(), count


class MongoPermisoRepository(AtomicMenuRepository):
    def _working(self, snapshot: MenuSnapshot) -> MongoPermisoWorkingRepository:
        return MongoPermisoWorkingRepository(snapshot)  # type: ignore[arg-type]

    def get_snapshot(self) -> AccessSnapshot:
        return self._read(lambda repository: cast(MongoPermisoWorkingRepository, repository)._snapshot())

    def apply_batch(self, data: AccessBatchRequest) -> tuple[AccessSnapshot, int]:
        return self.run_atomic(lambda repository: cast(MongoPermisoWorkingRepository, repository)._apply_batch(data))

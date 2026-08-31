from collections import defaultdict
from datetime import datetime, timezone
import re
import unicodedata
from typing import Any, Mapping

from bson import ObjectId, errors
from fastapi import HTTPException
from pymongo.database import Database

from app.modules.auth.schemas import (
    MenuAdminChild,
    MenuChild,
    MenuDataSacWebCreateRequest,
    MenuDataSacWebUpdateRequest,
)

MongoDocument = dict[str, Any]


class MongoMenuRepository:
    menu_collection_name = "menu"
    permisos_collection_name = "permisos"
    rol_permisos_collection_name = "rol_permisos"

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.menu_collection = mongo_db[self.menu_collection_name]
        self.permisos_collection = mongo_db[self.permisos_collection_name]
        self.rol_permisos_collection = mongo_db[self.rol_permisos_collection_name]

    def get_menu_by_role_codes(self, role_codes: list[str]) -> list[MenuChild]:
        if not role_codes:
            return []

        permisos_asignados = {
            str(documento["permiso_codigo"])
            for documento in self.rol_permisos_collection.find(
                {
                    "rol_codigo": {"$in": role_codes},
                    "activo": True,
                },
                {"_id": 0, "permiso_codigo": 1},
            )
            if documento.get("permiso_codigo")
        }
        if not permisos_asignados:
            return []

        permisos_activos = {
            str(documento["codigo"])
            for documento in self.permisos_collection.find(
                {
                    "codigo": {"$in": sorted(permisos_asignados)},
                    "activo": True,
                },
                {"_id": 0, "codigo": 1},
            )
            if documento.get("codigo")
        }
        if not permisos_activos:
            return []

        documentos_activos = [
            self._serialize_document(doc)
            for doc in self.menu_collection.find({"activo": True})
        ]
        # La autorizacion de una hoja tambien necesita todos sus contenedores.
        # Esto mantiene el arbol util durante la migracion de menus existentes y
        # complementa la sincronizacion que se hace al administrar una rama.
        autorizados = {
            documento["id"]
            for documento in documentos_activos
            if documento.get("permiso_requerido") in permisos_activos
        }
        padres_por_id = {
            documento["id"]: documento.get("id_padre")
            for documento in documentos_activos
        }
        for id_menu in list(autorizados):
            id_padre = padres_por_id.get(id_menu)
            while id_padre:
                autorizados.add(id_padre)
                id_padre = padres_por_id.get(id_padre)

        documentos = [
            documento for documento in documentos_activos if documento["id"] in autorizados
        ]
        return self._build_tree(documentos)

    def create_menu_node(self, data: MenuDataSacWebCreateRequest) -> MenuAdminChild:
        parent = self._resolve_parent(data.id_padre)
        label = self._normalize_required_text(data.label, "El titulo es obligatorio.")
        node = self._build_node_document(
            label=label,
            icon=data.icon,
            parent=parent,
            tipo=data.tipo,
            orden=data.orden,
            activo=data.activo,
        )
        node["id_padre"] = parent.get("_id") if parent else None
        if self.menu_collection.find_one({"codigo": node["codigo"]}):
            raise HTTPException(status_code=409, detail="Ya existe un menu con ese codigo jerarquico.")

        roles_directos = self._normalize_roles(data.roles_codigo)
        node["roles_directos_codigos"] = roles_directos
        now = self._now()
        node["created_at"] = now
        node["updated_at"] = now
        result = self.menu_collection.insert_one(node)
        self._ensure_permission(node)
        self._sync_effective_role_permissions()
        return self.get_menu_node(str(result.inserted_id))

    def update_menu_node(
        self,
        id_menu: str,
        data: MenuDataSacWebUpdateRequest,
    ) -> MenuAdminChild:
        object_id = self._resolve_object_id(id_menu)
        current = self.menu_collection.find_one({"_id": object_id})
        if not current:
            raise HTTPException(status_code=404, detail="Menu no encontrado.")

        changes = data.model_dump(exclude_unset=True)
        roles_directos = changes.pop("roles_codigo", None)
        parent = self._resolve_parent(changes.pop("id_padre", current.get("id_padre")), object_id)
        document = {**current, **changes}
        document["label"] = self._normalize_required_text(document["label"], "El titulo es obligatorio.")
        document["icon"] = self._normalize_optional_text(document.get("icon"))
        document["id_padre"] = parent.get("_id") if parent else None

        documents = list(self.menu_collection.find({}))
        descendants = self._collect_descendants(documents, object_id)
        descendant_ids = {doc["_id"] for doc in descendants}
        if parent and parent["_id"] in descendant_ids:
            raise HTTPException(status_code=400, detail="Un menu no puede ser padre de si mismo ni de un descendiente.")

        # El codigo, permiso y ruta de cada descendiente dependen de su padre;
        # por eso una edicion o movimiento de rama recalcula todo el subarbol.
        documents_by_parent: dict[ObjectId | None, list[dict[str, Any]]] = defaultdict(list)
        for item in descendants:
            documents_by_parent[item.get("id_padre")].append(item)
        regenerated: list[tuple[dict[str, Any], dict[str, Any]]] = []

        def regenerate(old: dict[str, Any], parent_doc: dict[str, Any] | None, override: dict[str, Any] | None = None) -> None:
            source = {**old, **(override or {})}
            new_doc = self._build_node_document(
                label=source["label"],
                icon=source.get("icon"),
                parent=parent_doc,
                tipo=source.get("tipo", "grupo"),
                orden=int(source.get("orden") or 1),
                activo=bool(source.get("activo", True)),
            )
            new_doc["id_padre"] = parent_doc.get("_id") if parent_doc else None
            regenerated.append((old, new_doc))
            for child in documents_by_parent.get(old["_id"], []):
                regenerate(child, {**new_doc, "_id": old["_id"]})

        regenerate(current, parent, document)
        new_codes = [new["codigo"] for _, new in regenerated]
        collision = self.menu_collection.find_one(
            {"_id": {"$nin": list(descendant_ids)}, "codigo": {"$in": new_codes}}
        )
        if collision:
            raise HTTPException(status_code=409, detail="La edicion genera un codigo jerarquico ya existente.")

        for old, new in regenerated:
            update_fields = {
                **new,
                "updated_at": self._now(),
            }
            if old["_id"] == object_id and roles_directos is not None:
                update_fields["roles_directos_codigos"] = self._normalize_roles(roles_directos)
            self.menu_collection.update_one({"_id": old["_id"]}, {"$set": update_fields})
            self._ensure_permission(update_fields)
            old_permission = old.get("permiso_requerido")
            if old_permission and old_permission != update_fields["permiso_requerido"]:
                self.permisos_collection.update_one({"codigo": old_permission}, {"$set": {"activo": False, "updated_at": self._now()}})
                self.rol_permisos_collection.update_many({"permiso_codigo": old_permission}, {"$set": {"activo": False, "updated_at": self._now()}})

        self._sync_effective_role_permissions()
        return self.get_menu_node(id_menu)

    def get_menu_node(self, id_menu: str) -> MenuAdminChild:
        object_id = self._resolve_object_id(id_menu)
        document = self.menu_collection.find_one({"_id": object_id})
        if not document:
            raise HTTPException(status_code=404, detail="Menu no encontrado.")
        roles = self._roles_by_permission()
        return self._to_admin_child(self._serialize_document(document), roles, [])

    def get_complete_menu_tree(self, activo: bool | None = None) -> list[MenuAdminChild]:
        query: dict[str, Any] = {} if activo is None else {"activo": activo}
        documentos = [
            self._serialize_document(doc)
            for doc in self.menu_collection.find(query)
        ]
        roles_por_permiso = self._roles_by_permission()

        hijos_por_padre: dict[str, list[dict[str, Any]]] = defaultdict(list)
        ids = {documento["id"] for documento in documentos}
        raices: list[dict[str, Any]] = []
        for documento in documentos:
            id_padre = documento.get("id_padre")
            if id_padre is None or id_padre not in ids:
                raices.append(documento)
            else:
                hijos_por_padre[id_padre].append(documento)

        for hijos in hijos_por_padre.values():
            hijos.sort(key=self._sort_key)

        def build_node(documento: Mapping[str, Any]) -> MenuAdminChild:
            return self._to_admin_child(
                documento,
                roles_por_permiso,
                [build_node(child) for child in hijos_por_padre.get(str(documento["id"]), [])],
            )

        raices.sort(key=self._sort_key)
        return [build_node(raiz) for raiz in raices]

    def delete_menu_node(self, id_menu: str) -> str:
        object_id = self._resolve_object_id(id_menu)
        document = self.menu_collection.find_one({"_id": object_id})
        if not document:
            raise HTTPException(status_code=404, detail="Menu no encontrado.")
        if self.menu_collection.find_one({"id_padre": object_id}, {"_id": 1}):
            raise HTTPException(status_code=409, detail="No se puede eliminar un menu que tiene hijos.")

        permission = str(document["permiso_requerido"])
        self.menu_collection.delete_one({"_id": object_id})
        self.rol_permisos_collection.delete_many({"permiso_codigo": permission})
        self.permisos_collection.delete_many({"codigo": permission})
        self._sync_effective_role_permissions()
        return permission

    def _build_tree(self, documentos: list[dict[str, Any]]) -> list[MenuChild]:
        hijos_por_padre: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for doc in documentos:
            id_padre = doc.get("id_padre")
            if id_padre:
                hijos_por_padre[str(id_padre)].append(doc)

        for hijos in hijos_por_padre.values():
            hijos.sort(key=self._sort_key)

        def build_node(doc: Mapping[str, Any]) -> MenuChild:
            children = [build_node(child) for child in hijos_por_padre.get(str(doc["id"]), [])]
            return MenuChild(
                label=str(doc.get("label") or ""),
                routerLink=doc.get("ruta"),
                icon=doc.get("icon"),
                children=children,
            )

        padres = [doc for doc in documentos if doc.get("id_padre") is None]
        padres.sort(key=self._sort_key)
        return [build_node(padre) for padre in padres]

    def _serialize_document(self, doc: Mapping[str, Any]) -> dict[str, Any]:
        result = dict(doc)
        result["id"] = self._object_id_to_str(result.pop("_id"))
        result["id_padre"] = self._object_id_to_str(result.get("id_padre"))
        if not result.get("ruta") and result.get("codigo"):
            # Los grupos historicos no tenian ruta. Se les entrega una ruta
            # determinista para abrir la pantalla intermedia sin migrar datos.
            result["ruta"] = self._route_from_code(str(result["codigo"]))
        return result

    def _object_id_to_str(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, ObjectId):
            return str(value)
        return str(value)

    def _sort_key(self, doc: Mapping[str, Any]) -> tuple[int, str]:
        return (int(doc.get("orden") or 0), str(doc.get("label") or "").lower())

    def _to_admin_child(
        self,
        documento: Mapping[str, Any],
        roles_por_permiso: Mapping[str, set[str]],
        children: list[MenuAdminChild],
    ) -> MenuAdminChild:
        permiso_requerido = str(documento.get("permiso_requerido") or "")
        return MenuAdminChild(
            id=str(documento["id"]),
            codigo=str(documento.get("codigo") or ""),
            label=str(documento.get("label") or ""),
            icon=documento.get("icon"),
            id_padre=documento.get("id_padre"),
            tipo=str(documento.get("tipo") or "grupo"),
            ruta=documento.get("ruta"),
            permiso_requerido=permiso_requerido,
            orden=int(documento.get("orden") or 0),
            activo=bool(documento.get("activo", False)),
            roles_permitidos_codigos=sorted(roles_por_permiso.get(permiso_requerido, set())),
            children=children,
        )

    def _roles_by_permission(self) -> dict[str, set[str]]:
        roles_por_permiso: dict[str, set[str]] = defaultdict(set)
        for documento in self.rol_permisos_collection.find(
            {"activo": True},
            {"_id": 0, "rol_codigo": 1, "permiso_codigo": 1},
        ):
            permiso_codigo = documento.get("permiso_codigo")
            rol_codigo = documento.get("rol_codigo")
            if permiso_codigo and rol_codigo:
                roles_por_permiso[str(permiso_codigo)].add(str(rol_codigo))
        return roles_por_permiso

    def _resolve_parent(
        self,
        id_padre: str | ObjectId | None,
        current_id: ObjectId | None = None,
    ) -> dict[str, Any] | None:
        if id_padre is None:
            return None
        object_id = id_padre if isinstance(id_padre, ObjectId) else self._resolve_object_id(id_padre)
        if current_id is not None and object_id == current_id:
            raise HTTPException(status_code=400, detail="Un menu no puede ser su propio padre.")
        parent = self.menu_collection.find_one({"_id": object_id})
        if not parent:
            raise HTTPException(status_code=404, detail="Menu padre no encontrado.")
        if parent.get("tipo", "grupo") != "grupo":
            raise HTTPException(status_code=400, detail="El menu padre debe ser de tipo grupo.")
        return parent

    def _build_node_document(
        self,
        *,
        label: str,
        icon: str | None,
        parent: Mapping[str, Any] | None,
        tipo: str,
        orden: int,
        activo: bool,
    ) -> dict[str, Any]:
        code_segment = self._code_segment(label)
        path_segment = self._path_segment(label)
        parent_code = str(parent.get("codigo")) if parent else ""
        parent_route = self._route_from_code(parent_code) if parent_code else "/dashboard"
        code = f"{parent_code}.{code_segment}" if parent_code else code_segment
        route = f"{parent_route.rstrip('/')}/{path_segment}"
        permission = f"{code.lower().replace('_', '.')}.ver"
        root_code = code.split(".")[0]
        return {
            "codigo": code,
            "label": label,
            "icon": self._normalize_optional_text(icon),
            "tipo": tipo,
            "ruta": route,
            "permiso_requerido": permission,
            "orden": orden,
            "activo": activo,
            "modulo_codigo": root_code,
        }

    def _collect_descendants(
        self,
        documents: list[dict[str, Any]],
        root_id: ObjectId,
    ) -> list[dict[str, Any]]:
        by_parent: dict[ObjectId, list[dict[str, Any]]] = defaultdict(list)
        by_id = {doc["_id"]: doc for doc in documents}
        for document in documents:
            if document.get("id_padre"):
                by_parent[document["id_padre"]].append(document)
        if root_id not in by_id:
            return []
        result: list[dict[str, Any]] = []

        def visit(node: dict[str, Any]) -> None:
            result.append(node)
            for child in by_parent.get(node["_id"], []):
                visit(child)

        visit(by_id[root_id])
        return result

    def _ensure_permission(self, menu: Mapping[str, Any]) -> None:
        permission = str(menu["permiso_requerido"])
        now = self._now()
        self.permisos_collection.update_one(
            {"codigo": permission},
            {
                "$set": {
                    "recurso": str(menu["codigo"]),
                    "modulo_codigo": str(menu.get("modulo_codigo") or str(menu["codigo"]).split(".")[0]),
                    "accion": "VER",
                    "activo": bool(menu.get("activo", True)),
                    "updated_at": now,
                },
                "$setOnInsert": {"codigo": permission, "created_at": now},
            },
            upsert=True,
        )

    def _sync_effective_role_permissions(self) -> None:
        """Sincroniza cada permiso con los roles efectivos de su subarbol.

        `roles_directos_codigos` pertenece al nodo editado. El permiso de cada
        ancestro se deriva de sus hijos, por lo que una hoja de cuarto nivel es
        visible desde todos los niveles anteriores sin duplicar decisiones en
        el cliente.
        """
        documents = list(self.menu_collection.find({}))
        children_by_parent: dict[ObjectId | None, list[dict[str, Any]]] = defaultdict(list)
        for document in documents:
            children_by_parent[document.get("id_padre")].append(document)
        current_roles = self._roles_by_permission()
        targets: dict[str, set[str]] = {}

        def effective_roles(document: dict[str, Any]) -> set[str]:
            child_roles: set[str] = set()
            for child in children_by_parent.get(document["_id"], []):
                child_roles.update(effective_roles(child))
            if not document.get("activo", True):
                targets[str(document["permiso_requerido"])] = set()
                return set()
            direct = document.get("roles_directos_codigos")
            if direct is None:
                # Compatibilidad con documentos anteriores: las hojas ya
                # asignadas conservan su lista; los grupos pasan a derivarla.
                direct = current_roles.get(str(document["permiso_requerido"]), set()) if not children_by_parent.get(document["_id"]) else set()
            roles = {str(role).strip() for role in direct if str(role).strip()} | child_roles
            targets[str(document["permiso_requerido"])] = roles
            return roles

        for root in children_by_parent.get(None, []):
            effective_roles(root)

        for permission, roles in targets.items():
            self._sync_roles_for_permission(permission, roles)

    def _sync_roles_for_permission(self, permission: str, roles: set[str]) -> None:
        now = self._now()
        existing = list(self.rol_permisos_collection.find({"permiso_codigo": permission}))
        existing_roles = {str(item.get("rol_codigo")) for item in existing if item.get("rol_codigo")}
        for relation in existing:
            role = str(relation.get("rol_codigo") or "")
            self.rol_permisos_collection.update_one(
                {"_id": relation["_id"]},
                {"$set": {"activo": role in roles, "updated_at": now}},
            )
        for role in roles - existing_roles:
            self.rol_permisos_collection.insert_one(
                {
                    "rol_codigo": role,
                    "permiso_codigo": permission,
                    "activo": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )

    def _resolve_object_id(self, id_menu: str) -> ObjectId:
        try:
            return ObjectId(id_menu)
        except (errors.InvalidId, TypeError) as exc:
            raise HTTPException(status_code=400, detail="ID de menu invalido.") from exc

    def _normalize_roles(self, roles: list[str]) -> list[str]:
        return list(dict.fromkeys(role.strip() for role in roles if role.strip()))

    def _normalize_required_text(self, value: str, detail: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise HTTPException(status_code=400, detail=detail)
        return normalized

    def _normalize_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _code_segment(self, label: str) -> str:
        normalized = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
        segment = re.sub(r"[^A-Za-z0-9]+", "_", normalized).strip("_").upper()
        if not segment:
            raise HTTPException(status_code=400, detail="El titulo no genera un codigo valido.")
        return segment

    def _path_segment(self, label: str) -> str:
        normalized = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
        segment = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
        if not segment:
            raise HTTPException(status_code=400, detail="El titulo no genera una ruta valida.")
        return segment

    def _route_from_code(self, code: str) -> str:
        segments = [segment.lower().replace("_", "-") for segment in code.split(".") if segment]
        return "/dashboard/" + "/".join(segments)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

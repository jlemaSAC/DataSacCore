from collections import defaultdict
from typing import Any, Mapping

from bson import ObjectId
from pymongo.database import Database

from app.modules.auth.schemas import MenuAdminChild, MenuChild

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

        documentos = [
            self._serialize_document(doc)
            for doc in self.menu_collection.find(
                {
                    "activo": True,
                    "permiso_requerido": {"$in": sorted(permisos_activos)},
                },
            )
        ]
        return self._build_tree(documentos)

    def get_complete_menu_tree(self) -> list[MenuAdminChild]:
        documentos = [
            self._serialize_document(doc)
            for doc in self.menu_collection.find({})
        ]
        roles_por_permiso: dict[str, set[str]] = defaultdict(set)
        for documento in self.rol_permisos_collection.find(
            {"activo": True},
            {"_id": 0, "rol_codigo": 1, "permiso_codigo": 1},
        ):
            permiso_codigo = documento.get("permiso_codigo")
            rol_codigo = documento.get("rol_codigo")
            if permiso_codigo and rol_codigo:
                roles_por_permiso[str(permiso_codigo)].add(str(rol_codigo))

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
                children=[build_node(child) for child in hijos_por_padre.get(str(documento["id"]), [])],
            )

        raices.sort(key=self._sort_key)
        return [build_node(raiz) for raiz in raices]

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
        return result

    def _object_id_to_str(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, ObjectId):
            return str(value)
        return str(value)

    def _sort_key(self, doc: Mapping[str, Any]) -> tuple[int, str]:
        return (int(doc.get("orden") or 0), str(doc.get("label") or "").lower())

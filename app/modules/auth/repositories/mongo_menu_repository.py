from collections import defaultdict
from typing import Any, Mapping

from bson import ObjectId
from pymongo.database import Database

from app.modules.auth.schemas import MenuChild

MongoDocument = dict[str, Any]

class MongoMenuRepository:
    collection_name = "MenuPermisosDataSAC"

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.collection = mongo_db[self.collection_name]

    def get_menu_by_role_codes(self, role_codes: list[str]) -> list[MenuChild]:
        if not role_codes:
            return []

        documentos = [
            self._serialize_document(doc)
            for doc in self.collection.find(
                {
                    "activo": True,
                    "rolesPermitidosCodigos": {"$in": role_codes},
                }
            )
        ]
        return self._build_tree(documentos)

    def _build_tree(self, documentos: list[dict[str, Any]]) -> list[MenuChild]:
        hijos_por_padre: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for doc in documentos:
            id_padre = doc.get("idPadre")
            if id_padre:
                hijos_por_padre[str(id_padre)].append(doc)

        for hijos in hijos_por_padre.values():
            hijos.sort(key=self._sort_key)

        def build_node(doc: Mapping[str, Any]) -> MenuChild:
            children = [build_node(child) for child in hijos_por_padre.get(str(doc["id"]), [])]
            return MenuChild(
                label=str(doc.get("label") or ""),
                routerLink=doc.get("routerLink"),
                icon=doc.get("icon"),
                children=children,
            )

        padres = [doc for doc in documentos if doc.get("idPadre") is None]
        padres.sort(key=self._sort_key)
        return [build_node(padre) for padre in padres]

    def _serialize_document(self, doc: Mapping[str, Any]) -> dict[str, Any]:
        result = dict(doc)
        result["id"] = self._object_id_to_str(result.pop("_id"))
        result["idPadre"] = self._object_id_to_str(result.get("idPadre"))
        return result

    def _object_id_to_str(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, ObjectId):
            return str(value)
        return str(value)

    def _sort_key(self, doc: Mapping[str, Any]) -> str:
        return str(doc.get("label") or "").lower()

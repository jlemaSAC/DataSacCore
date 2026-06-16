from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId, errors
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.database import Database

from app.modules.analytic.menu.schemas import (
    MenuAnalyticAdminResponse,
    MenuAnalyticAdminTreeResponse,
    MenuAnalyticCreateRequest,
    MenuAnalyticDeleteResponse,
    MenuAnalyticResponse,
    MenuAnalyticUpdateRequest,
    PermisoAnalyticAdminResponse,
    PermisoAnalyticCreateRequest,
    RolPermisoAnalyticAdminResponse,
    RolPermisoAnalyticCreateRequest,
)

MongoDocument = dict[str, Any]


class MongoMenuAnalyticAdminRepository:
    menu_collection_name = "menu"
    permisos_collection_name = "permisos"
    rol_permisos_collection_name = "rol_permisos"

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.menu_collection = mongo_db[self.menu_collection_name]
        self.permisos_collection = mongo_db[self.permisos_collection_name]
        self.rol_permisos_collection = mongo_db[self.rol_permisos_collection_name]

    def get_menu_by_roles(self, roles_codigo: list[str]) -> list[MenuAnalyticResponse]:
        permisos_usuario = self.get_permission_documents_by_roles(roles_codigo)
        codigos_permisos_usuario = {
            permiso["codigo"]
            for permiso in permisos_usuario
            if permiso.get("codigo")
        }
        if not codigos_permisos_usuario:
            return []

        documentos = list(
            self.menu_collection.find(
                {
                    "activo": True,
                    "permiso_requerido": {"$in": list(codigos_permisos_usuario)},
                }
            ).sort("orden", 1)
        )

        return self._build_authorized_menu_tree(documentos, permisos_usuario)

    def get_effective_permissions_by_roles(self, roles_codigo: list[str]) -> set[str]:
        permisos = self.get_permission_documents_by_roles(roles_codigo)
        return {
            permiso["codigo"]
            for permiso in permisos
            if permiso.get("codigo")
        }

    def get_permission_documents_by_roles(
        self,
        roles_codigo: list[str],
    ) -> list[dict[str, Any]]:
        roles = self._normalizar_roles_requeridos(roles_codigo)

        relaciones = self.rol_permisos_collection.find(
            {
                "rol_codigo": {"$in": roles},
                "activo": True,
            },
            {"_id": 0, "permiso_codigo": 1},
        )

        codigos_asignados = {
            relacion["permiso_codigo"]
            for relacion in relaciones
            if relacion.get("permiso_codigo")
        }
        if not codigos_asignados:
            return []

        return list(
            self.permisos_collection.find(
                {
                    "codigo": {"$in": list(codigos_asignados)},
                    "activo": True,
                },
                {
                    "_id": 0,
                    "codigo": 1,
                    "recurso": 1,
                    "modulo_codigo": 1,
                    "accion": 1,
                },
            )
        )

    def create_menu_route(
        self,
        data: MenuAnalyticCreateRequest,
    ) -> MenuAnalyticAdminResponse:
        roles_codigo = self._normalizar_roles_codigo(data.roles_codigo)
        documento = data.model_dump(exclude={"roles_codigo"})
        documento["codigo"] = documento["codigo"].strip()
        documento["label"] = documento["label"].strip()
        documento["permiso_requerido"] = documento["permiso_requerido"].strip()
        documento["ruta"] = self._normalizar_texto_opcional(documento.get("ruta"))
        documento["icon"] = self._normalizar_texto_opcional(documento.get("icon"))

        self._validar_documento_menu(documento)
        self._validar_campos_obligatorios_menu(documento)

        existe_codigo = self.menu_collection.find_one({"codigo": documento["codigo"]})
        if existe_codigo:
            raise HTTPException(status_code=409, detail="Ya existe un menu con ese codigo.")

        id_padre, padre = self._resolver_padre(documento.get("id_padre"))
        documento["id_padre"] = id_padre
        self._asignar_timestamps_creacion(documento)

        permisos = self._crear_permisos_por_defecto(documento, padre)
        rol_permisos = [
            self._crear_o_reactivar_rol_permiso(
                rol_codigo=rol_codigo,
                permiso_codigo=permiso.codigo,
            )
            for permiso in permisos
            for rol_codigo in roles_codigo
        ]

        resultado = self.menu_collection.insert_one(documento)
        response_payload = {
            **documento,
            "id": str(resultado.inserted_id),
            "id_padre": str(id_padre) if id_padre else None,
            "roles_codigo": roles_codigo,
            "permisos": permisos,
            "rol_permisos": rol_permisos,
        }

        return MenuAnalyticAdminResponse(**response_payload)

    def list_menu_routes(
        self,
        activo: bool | None = None,
    ) -> list[MenuAnalyticAdminResponse]:
        filtro: dict[str, Any] = {}
        if activo is not None:
            filtro["activo"] = activo

        documentos = self.menu_collection.find(filtro).sort("orden", 1)
        return [self._serializar_menu_admin_response(documento) for documento in documentos]

    def list_menu_tree(
        self,
        activo: bool | None = None,
    ) -> list[MenuAnalyticAdminTreeResponse]:
        filtro: dict[str, Any] = {}
        if activo is not None:
            filtro["activo"] = activo

        documentos = list(self.menu_collection.find(filtro).sort("orden", 1))
        documentos_serializados = [
            self._serializar_menu_admin_tree_documento(documento)
            for documento in documentos
        ]
        ids_disponibles = {documento["id"] for documento in documentos_serializados}

        hijos_por_padre: dict[str, list[dict[str, Any]]] = {}
        raices: list[dict[str, Any]] = []
        for documento in documentos_serializados:
            id_padre = documento.get("id_padre")
            if id_padre is None or id_padre not in ids_disponibles:
                raices.append(documento)
                continue
            hijos_por_padre.setdefault(id_padre, []).append(documento)

        def construir_nodo(documento: dict[str, Any]) -> MenuAnalyticAdminTreeResponse:
            hijos = sorted(
                hijos_por_padre.get(documento["id"], []),
                key=lambda item: (item["orden"], item["label"].lower()),
            )
            return MenuAnalyticAdminTreeResponse(
                **documento,
                children=[construir_nodo(hijo) for hijo in hijos],
            )

        raices_ordenadas = sorted(
            raices,
            key=lambda item: (item["orden"], item["label"].lower()),
        )
        return [construir_nodo(raiz) for raiz in raices_ordenadas]

    def get_menu_route(self, id_menu: str) -> MenuAnalyticAdminResponse:
        object_id = self._resolver_object_id(id_menu, "ID de menu invalido.")
        documento = self.menu_collection.find_one({"_id": object_id})
        if not documento:
            raise HTTPException(status_code=404, detail="Menu no encontrado.")

        return self._serializar_menu_admin_response(documento)

    def update_menu_route(
        self,
        id_menu: str,
        data: MenuAnalyticUpdateRequest,
    ) -> MenuAnalyticAdminResponse:
        object_id = self._resolver_object_id(id_menu, "ID de menu invalido.")
        documento_actual = self.menu_collection.find_one({"_id": object_id})
        if not documento_actual:
            raise HTTPException(status_code=404, detail="Menu no encontrado.")

        cambios = data.model_dump(exclude_unset=True)
        roles_codigo = cambios.pop("roles_codigo", None)
        cambios = self._normalizar_cambios_menu(object_id, documento_actual, cambios)

        documento_final = {**documento_actual, **cambios}
        self._validar_documento_menu(documento_final)

        if cambios.get("codigo") and cambios["codigo"] != documento_actual.get("codigo"):
            existe_codigo = self.menu_collection.find_one(
                {
                    "_id": {"$ne": object_id},
                    "codigo": cambios["codigo"],
                }
            )
            if existe_codigo:
                raise HTTPException(status_code=409, detail="Ya existe un menu con ese codigo.")

        permisos = []
        rol_permisos = []
        if "permiso_requerido" in cambios or "codigo" in cambios or "id_padre" in cambios:
            padre = self._find_parent_for_document(documento_final)
            permisos = self._crear_permisos_por_defecto(documento_final, padre)

        if roles_codigo is not None:
            roles = self._normalizar_roles_codigo(roles_codigo)
            permisos_asignar = permisos
            if not permisos_asignar:
                padre = self._find_parent_for_document(documento_final)
                permisos_asignar = [
                    self._crear_o_obtener_permiso(
                        codigo=documento_final["permiso_requerido"],
                        recurso=documento_final["codigo"],
                        modulo_codigo=self._resolver_modulo_codigo(documento_final, padre),
                        accion=self._resolver_accion_permiso(documento_final["permiso_requerido"]),
                    )
                ]

            rol_permisos = [
                self._crear_o_reactivar_rol_permiso(
                    rol_codigo=rol_codigo,
                    permiso_codigo=permiso.codigo,
                )
                for permiso in permisos_asignar
                for rol_codigo in roles
            ]

        if not cambios:
            response = self._serializar_menu_admin_response(documento_actual)
            response.permisos = permisos
            response.rol_permisos = rol_permisos
            return response

        cambios["updated_at"] = self._fecha_actual_utc()
        documento_actualizado = self.menu_collection.find_one_and_update(
            {"_id": object_id},
            {"$set": cambios},
            return_document=ReturnDocument.AFTER,
        )
        if not documento_actualizado:
            raise HTTPException(status_code=404, detail="Menu no encontrado.")

        response = self._serializar_menu_admin_response(documento_actualizado)
        response.permisos = permisos
        response.rol_permisos = rol_permisos
        return response

    def delete_menu_route(self, id_menu: str) -> MenuAnalyticDeleteResponse:
        object_id = self._resolver_object_id(id_menu, "ID de menu invalido.")
        documento = self.menu_collection.find_one({"_id": object_id})
        if not documento:
            raise HTTPException(status_code=404, detail="Menu no encontrado.")

        hijo = self.menu_collection.find_one({"id_padre": object_id}, {"_id": 1})
        if hijo:
            raise HTTPException(
                status_code=409,
                detail="No se puede eliminar un padre con rutas hijas.",
            )

        permiso_codigo = documento["permiso_requerido"]
        resultado_menu = self.menu_collection.delete_one({"_id": object_id})
        resultado_rol_permisos = self.rol_permisos_collection.delete_many(
            {"permiso_codigo": permiso_codigo}
        )
        resultado_permisos = self.permisos_collection.delete_many({"codigo": permiso_codigo})

        return MenuAnalyticDeleteResponse(
            id=str(object_id),
            permiso_codigo=permiso_codigo,
            rutas_eliminadas=resultado_menu.deleted_count,
            permisos_eliminados=resultado_permisos.deleted_count,
            rol_permisos_eliminados=resultado_rol_permisos.deleted_count,
            detail="Ruta, permiso y relaciones rol-permiso eliminadas correctamente.",
        )

    def create_permission(
        self,
        data: PermisoAnalyticCreateRequest,
    ) -> PermisoAnalyticAdminResponse:
        documento = data.model_dump()
        documento["codigo"] = documento["codigo"].strip()
        documento["recurso"] = documento["recurso"].strip()
        documento["modulo_codigo"] = self._normalizar_texto_opcional(
            documento.get("modulo_codigo")
        )
        documento["accion"] = self._normalizar_accion_permiso(documento["accion"])
        self._asignar_timestamps_creacion(documento)

        if not documento["codigo"]:
            raise HTTPException(status_code=400, detail="El codigo es obligatorio.")
        if not documento["recurso"]:
            raise HTTPException(status_code=400, detail="El recurso es obligatorio.")
        if not documento["accion"]:
            raise HTTPException(status_code=400, detail="La accion es obligatoria.")

        existe_codigo = self.permisos_collection.find_one({"codigo": documento["codigo"]})
        if existe_codigo:
            raise HTTPException(status_code=409, detail="Ya existe un permiso con ese codigo.")

        resultado = self.permisos_collection.insert_one(documento)
        return PermisoAnalyticAdminResponse(id=str(resultado.inserted_id), **documento)

    def create_role_permission(
        self,
        data: RolPermisoAnalyticCreateRequest,
    ) -> RolPermisoAnalyticAdminResponse:
        documento = data.model_dump()
        documento["rol_codigo"] = documento["rol_codigo"].strip()
        documento["permiso_codigo"] = documento["permiso_codigo"].strip()
        documento["rol_nombre"] = self._resolver_rol_nombre(documento["rol_codigo"])
        self._asignar_timestamps_creacion(documento)

        if not documento["rol_codigo"]:
            raise HTTPException(status_code=400, detail="El rol es obligatorio.")
        if not documento["permiso_codigo"]:
            raise HTTPException(status_code=400, detail="El permiso es obligatorio.")

        permiso = self.permisos_collection.find_one(
            {
                "codigo": documento["permiso_codigo"],
                "activo": True,
            }
        )
        if not permiso:
            raise HTTPException(status_code=404, detail="Permiso no encontrado o inactivo.")

        existe_relacion = self.rol_permisos_collection.find_one(
            {
                "rol_codigo": documento["rol_codigo"],
                "permiso_codigo": documento["permiso_codigo"],
            }
        )
        if existe_relacion:
            raise HTTPException(
                status_code=409,
                detail="El rol ya tiene registrado ese permiso.",
            )

        resultado = self.rol_permisos_collection.insert_one(documento)
        return RolPermisoAnalyticAdminResponse(id=str(resultado.inserted_id), **documento)

    def _serializar_menu_admin_response(
        self,
        documento: dict[str, Any],
    ) -> MenuAnalyticAdminResponse:
        permiso_requerido = documento["permiso_requerido"]
        roles_codigo = self._obtener_roles_por_permiso(permiso_requerido)

        return MenuAnalyticAdminResponse(
            id=str(documento["_id"]),
            codigo=documento["codigo"],
            label=documento["label"],
            icon=documento.get("icon"),
            id_padre=str(documento["id_padre"]) if documento.get("id_padre") else None,
            tipo=documento["tipo"],
            ruta=documento.get("ruta"),
            permiso_requerido=permiso_requerido,
            orden=int(documento["orden"]),
            activo=bool(documento.get("activo", True)),
            roles_codigo=roles_codigo,
            created_at=documento.get("created_at"),
            updated_at=documento.get("updated_at"),
        )

    def _serializar_menu_admin_tree_documento(self, documento: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(documento["_id"]),
            "codigo": documento["codigo"],
            "label": documento["label"],
            "icon": documento.get("icon"),
            "id_padre": str(documento["id_padre"]) if documento.get("id_padre") else None,
            "tipo": documento["tipo"],
            "ruta": documento.get("ruta"),
            "permiso_requerido": documento["permiso_requerido"],
            "orden": int(documento["orden"]),
            "activo": bool(documento.get("activo", True)),
            "created_at": documento.get("created_at"),
            "updated_at": documento.get("updated_at"),
        }

    def _build_authorized_menu_tree(
        self,
        documentos: list[dict[str, Any]],
        permisos_usuario: list[dict[str, Any]] | None = None,
    ) -> list[MenuAnalyticResponse]:
        documentos_serializados = [
            self._serializar_menu_documento(documento)
            for documento in documentos
        ]
        permisos_usuario = permisos_usuario or []
        ids_autorizados = {documento["id"] for documento in documentos_serializados}

        hijos_por_padre: dict[str, list[dict[str, Any]]] = defaultdict(list)
        raices: list[dict[str, Any]] = []

        for documento in documentos_serializados:
            id_padre = documento.get("id_padre")
            if id_padre is None:
                raices.append(documento)
                continue

            if id_padre in ids_autorizados:
                hijos_por_padre[id_padre].append(documento)

        def construir_nodo(documento: dict[str, Any]) -> MenuAnalyticResponse:
            hijos = sorted(
                hijos_por_padre.get(documento["id"], []),
                key=lambda item: (item["orden"], item["label"].lower()),
            )
            return MenuAnalyticResponse(
                id=documento["id"],
                codigo=documento["codigo"],
                label=documento["label"],
                icon=documento.get("icon"),
                tipo=documento["tipo"],
                ruta=documento.get("ruta"),
                permiso_requerido=documento["permiso_requerido"],
                permisos=self._obtener_permisos_del_nodo(documento, permisos_usuario),
                orden=documento["orden"],
                children=[construir_nodo(hijo) for hijo in hijos],
            )

        raices_ordenadas = sorted(
            raices,
            key=lambda item: (item["orden"], item["label"].lower()),
        )
        return [construir_nodo(raiz) for raiz in raices_ordenadas]

    def _serializar_menu_documento(self, documento: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(documento["_id"]),
            "codigo": documento["codigo"],
            "label": documento["label"],
            "icon": documento.get("icon"),
            "id_padre": str(documento["id_padre"]) if documento.get("id_padre") is not None else None,
            "tipo": documento["tipo"],
            "ruta": documento.get("ruta"),
            "permiso_requerido": documento["permiso_requerido"],
            "orden": int(documento["orden"]),
        }

    def _obtener_permisos_del_nodo(
        self,
        documento: dict[str, Any],
        permisos_usuario: list[dict[str, Any]],
    ) -> list[str]:
        permiso_requerido = documento["permiso_requerido"]
        codigos_por_recurso = [
            permiso["codigo"]
            for permiso in permisos_usuario
            if permiso.get("codigo") and permiso.get("recurso") == documento["codigo"]
        ]

        if codigos_por_recurso:
            return self._ordenar_permisos(codigos_por_recurso, permiso_requerido)

        codigos_usuario = {
            permiso["codigo"]
            for permiso in permisos_usuario
            if permiso.get("codigo")
        }

        if documento["tipo"] == "ruta":
            prefijo_funcional = permiso_requerido.rsplit(".", 1)[0]
            codigos_por_prefijo = [
                codigo
                for codigo in codigos_usuario
                if codigo == permiso_requerido or codigo.startswith(f"{prefijo_funcional}.")
            ]
            if codigos_por_prefijo:
                return self._ordenar_permisos(codigos_por_prefijo, permiso_requerido)

        if permiso_requerido in codigos_usuario or not permisos_usuario:
            return [permiso_requerido]

        return []

    def _ordenar_permisos(
        self,
        permisos: list[str],
        permiso_requerido: str,
    ) -> list[str]:
        permisos_unicos = list(dict.fromkeys(permisos))
        return sorted(
            permisos_unicos,
            key=lambda permiso: (
                permiso != permiso_requerido,
                permiso,
            ),
        )

    def _obtener_roles_por_permiso(self, permiso_codigo: str) -> list[str]:
        relaciones = self.rol_permisos_collection.find(
            {
                "permiso_codigo": permiso_codigo,
                "activo": True,
            },
            {"_id": 0, "rol_codigo": 1},
        )

        return list(
            dict.fromkeys(
                relacion["rol_codigo"]
                for relacion in relaciones
                if relacion.get("rol_codigo")
            )
        )

    def _normalizar_cambios_menu(
        self,
        object_id: ObjectId,
        documento_actual: dict[str, Any],
        cambios: dict[str, Any],
    ) -> dict[str, Any]:
        for campo in ("codigo", "label", "permiso_requerido"):
            if campo in cambios:
                cambios[campo] = cambios[campo].strip()
                if not cambios[campo]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"El campo {campo} es obligatorio.",
                    )

        if "icon" in cambios:
            cambios["icon"] = self._normalizar_texto_opcional(cambios.get("icon"))
        if "ruta" in cambios:
            cambios["ruta"] = self._normalizar_texto_opcional(cambios.get("ruta"))

        if "id_padre" in cambios:
            id_padre = self._normalizar_texto_opcional(cambios.get("id_padre"))
            if id_padre is None:
                cambios["id_padre"] = None
            else:
                id_padre_object, _ = self._resolver_padre(id_padre)
                if id_padre_object == object_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Un menu no puede ser padre de si mismo.",
                    )
                self._validar_no_ciclo(object_id, id_padre_object)
                cambios["id_padre"] = id_padre_object

        if "tipo" in cambios and cambios["tipo"] == "ruta":
            tiene_hijos = self.menu_collection.find_one(
                {
                    "id_padre": object_id,
                    "activo": True,
                },
                {"_id": 1},
            )
            if tiene_hijos:
                raise HTTPException(
                    status_code=409,
                    detail="No se puede convertir a ruta un grupo con hijos activos.",
                )

        return cambios

    def _validar_no_ciclo(self, object_id: ObjectId, nuevo_padre_id: ObjectId) -> None:
        actual: ObjectId | None = nuevo_padre_id
        while actual is not None:
            if actual == object_id:
                raise HTTPException(
                    status_code=400,
                    detail="No se puede mover un menu debajo de uno de sus descendientes.",
                )

            padre = self.menu_collection.find_one({"_id": actual}, {"id_padre": 1})
            if not padre or not padre.get("id_padre"):
                break
            actual = padre["id_padre"]

    def _validar_campos_obligatorios_menu(self, documento: dict[str, Any]) -> None:
        if not documento["codigo"]:
            raise HTTPException(status_code=400, detail="El codigo es obligatorio.")
        if not documento["label"]:
            raise HTTPException(status_code=400, detail="El label es obligatorio.")
        if not documento["permiso_requerido"]:
            raise HTTPException(status_code=400, detail="El permiso requerido es obligatorio.")

    def _validar_documento_menu(self, documento: dict[str, Any]) -> None:
        if documento["tipo"] == "grupo" and documento.get("ruta") is not None:
            raise HTTPException(status_code=400, detail="Un nodo tipo grupo no debe tener ruta.")
        if documento["tipo"] == "ruta" and documento.get("ruta") is None:
            raise HTTPException(status_code=400, detail="Un nodo tipo ruta debe tener ruta.")

    def _resolver_object_id(self, id_value: str, mensaje_error: str) -> ObjectId:
        try:
            return ObjectId(id_value)
        except errors.InvalidId as exc:
            raise HTTPException(status_code=400, detail=mensaje_error) from exc

    def _resolver_padre(
        self,
        id_padre: str | None,
    ) -> tuple[ObjectId | None, dict[str, Any] | None]:
        id_padre = self._normalizar_texto_opcional(id_padre)
        if id_padre is None:
            return None, None

        try:
            object_id = ObjectId(id_padre)
        except errors.InvalidId as exc:
            raise HTTPException(status_code=400, detail="id_padre invalido.") from exc

        padre = self.menu_collection.find_one(
            {
                "_id": object_id,
                "activo": True,
            }
        )
        if not padre:
            raise HTTPException(status_code=404, detail="Padre no encontrado.")
        if padre.get("tipo") != "grupo":
            raise HTTPException(status_code=400, detail="El padre debe ser un nodo tipo grupo.")

        return object_id, padre

    def _crear_permisos_por_defecto(
        self,
        documento: dict[str, Any],
        padre: dict[str, Any] | None,
    ) -> list[PermisoAnalyticAdminResponse]:
        permisos = [
            self._crear_o_obtener_permiso(
                codigo=documento["permiso_requerido"],
                recurso=documento["codigo"],
                modulo_codigo=self._resolver_modulo_codigo(documento, padre),
                accion=self._resolver_accion_permiso(documento["permiso_requerido"]),
            )
        ]

        if padre and padre.get("permiso_requerido"):
            permiso_padre = self._crear_o_obtener_permiso(
                codigo=padre["permiso_requerido"],
                recurso=padre["codigo"],
                modulo_codigo=padre.get("codigo"),
                accion=self._resolver_accion_permiso(padre["permiso_requerido"]),
            )
            permisos.append(permiso_padre)

        return self._deduplicar_permisos_response(permisos)

    def _crear_o_obtener_permiso(
        self,
        codigo: str,
        recurso: str,
        modulo_codigo: str | None,
        accion: str,
    ) -> PermisoAnalyticAdminResponse:
        documento = {
            "codigo": codigo,
            "recurso": recurso,
            "modulo_codigo": modulo_codigo,
            "accion": accion,
            "activo": True,
        }

        existente = self.permisos_collection.find_one({"codigo": codigo})
        if existente:
            if not existente.get("activo"):
                raise HTTPException(
                    status_code=409,
                    detail=f"El permiso {codigo} ya existe pero esta inactivo.",
                )
            return PermisoAnalyticAdminResponse(
                id=str(existente["_id"]),
                codigo=existente["codigo"],
                recurso=existente["recurso"],
                modulo_codigo=existente.get("modulo_codigo"),
                accion=existente["accion"],
                activo=existente["activo"],
                created_at=existente.get("created_at"),
                updated_at=existente.get("updated_at"),
            )

        self._asignar_timestamps_creacion(documento)
        resultado = self.permisos_collection.insert_one(documento)
        return PermisoAnalyticAdminResponse(id=str(resultado.inserted_id), **documento)

    def _crear_o_reactivar_rol_permiso(
        self,
        rol_codigo: str,
        permiso_codigo: str,
    ) -> RolPermisoAnalyticAdminResponse:
        documento = {
            "rol_codigo": rol_codigo,
            "rol_nombre": self._resolver_rol_nombre(rol_codigo),
            "permiso_codigo": permiso_codigo,
            "activo": True,
        }

        existente = self.rol_permisos_collection.find_one(
            {
                "rol_codigo": rol_codigo,
                "permiso_codigo": permiso_codigo,
            }
        )
        if existente:
            debe_actualizar = (
                not existente.get("activo")
                or existente.get("rol_nombre") != documento["rol_nombre"]
            )
            if debe_actualizar:
                updated_at = self._fecha_actual_utc()
                self.rol_permisos_collection.update_one(
                    {"_id": existente["_id"]},
                    {
                        "$set": {
                            "activo": True,
                            "rol_nombre": documento["rol_nombre"],
                            "updated_at": updated_at,
                        }
                    },
                )
                existente["rol_nombre"] = documento["rol_nombre"]
                existente["activo"] = True
                existente["updated_at"] = updated_at
            return RolPermisoAnalyticAdminResponse(
                id=str(existente["_id"]),
                rol_codigo=existente["rol_codigo"],
                rol_nombre=existente.get("rol_nombre"),
                permiso_codigo=existente["permiso_codigo"],
                activo=True,
                created_at=existente.get("created_at"),
                updated_at=existente.get("updated_at"),
            )

        self._asignar_timestamps_creacion(documento)
        resultado = self.rol_permisos_collection.insert_one(documento)
        return RolPermisoAnalyticAdminResponse(id=str(resultado.inserted_id), **documento)

    def _find_parent_for_document(self, documento: dict[str, Any]) -> dict[str, Any] | None:
        if not documento.get("id_padre"):
            return None
        return self.menu_collection.find_one({"_id": documento["id_padre"]})

    def _resolver_modulo_codigo(
        self,
        documento: dict[str, Any],
        padre: dict[str, Any] | None,
    ) -> str:
        if padre:
            return padre["codigo"]
        return documento["codigo"]

    def _resolver_accion_permiso(self, permiso_codigo: str) -> str:
        return self._normalizar_accion_permiso(permiso_codigo.rsplit(".", 1)[-1])

    def _normalizar_accion_permiso(self, accion: str) -> str:
        accion = accion.strip()
        if accion.lower() == "ver":
            return "VER"
        return accion

    def _deduplicar_permisos_response(
        self,
        permisos: list[PermisoAnalyticAdminResponse],
    ) -> list[PermisoAnalyticAdminResponse]:
        permisos_por_codigo = {}
        for permiso in permisos:
            permisos_por_codigo[permiso.codigo] = permiso
        return list(permisos_por_codigo.values())

    def _normalizar_roles_codigo(self, roles_codigo: list[str]) -> list[str]:
        roles = [
            rol.strip()
            for rol in roles_codigo
            if rol.strip()
        ]
        if not roles:
            return ["001"]
        return list(dict.fromkeys(roles))

    def _normalizar_roles_requeridos(self, roles_codigo: list[str]) -> list[str]:
        roles = [
            rol.strip()
            for rol in roles_codigo
            if rol.strip()
        ]
        if not roles:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar al menos un rol valido.",
            )
        return list(dict.fromkeys(roles))

    def _normalizar_texto_opcional(self, valor: str | None) -> str | None:
        if valor is None:
            return None

        valor = valor.strip()
        if not valor or valor.lower() == "null":
            return None

        return valor

    def _asignar_timestamps_creacion(self, documento: dict[str, Any]) -> None:
        ahora = self._fecha_actual_utc()
        documento["created_at"] = ahora
        documento["updated_at"] = ahora

    def _fecha_actual_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def _resolver_rol_nombre(self, rol_codigo: str) -> str:
        if rol_codigo == "001":
            return "ADMINISTRADOR"
        return rol_codigo

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MenuAnalyticResponse(BaseModel):
    id: str
    codigo: str
    label: str
    icon: str | None = None
    tipo: Literal["grupo", "ruta"]
    ruta: str | None = None
    permiso_requerido: str
    permisos: list[str] = Field(default_factory=list)
    orden: int = Field(ge=1)
    children: list["MenuAnalyticResponse"] = Field(default_factory=list)


class MenuAnalyticCreateRequest(BaseModel):
    codigo: str = Field(min_length=1)
    label: str = Field(min_length=1)
    icon: str | None = None
    id_padre: str | None = None
    tipo: Literal["grupo", "ruta"]
    ruta: str | None = None
    permiso_requerido: str = Field(min_length=1)
    orden: int = Field(ge=1)
    activo: bool = True
    roles_codigo: list[str] = Field(default_factory=lambda: ["001"])


class MenuAnalyticUpdateRequest(BaseModel):
    codigo: str | None = Field(default=None, min_length=1)
    label: str | None = Field(default=None, min_length=1)
    icon: str | None = None
    id_padre: str | None = None
    tipo: Literal["grupo", "ruta"] | None = None
    ruta: str | None = None
    permiso_requerido: str | None = Field(default=None, min_length=1)
    orden: int | None = Field(default=None, ge=1)
    activo: bool | None = None
    roles_codigo: list[str] | None = None


class PermisoAnalyticCreateRequest(BaseModel):
    codigo: str = Field(min_length=1)
    recurso: str = Field(min_length=1)
    modulo_codigo: str | None = None
    accion: str = Field(min_length=1)
    activo: bool = True


class PermisoAnalyticAdminResponse(PermisoAnalyticCreateRequest):
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RolPermisoAnalyticCreateRequest(BaseModel):
    rol_codigo: str = Field(min_length=1)
    permiso_codigo: str = Field(min_length=1)
    activo: bool = True


class RolPermisoAnalyticAdminResponse(RolPermisoAnalyticCreateRequest):
    id: str
    rol_nombre: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MenuAnalyticAdminResponse(MenuAnalyticCreateRequest):
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    permisos: list[PermisoAnalyticAdminResponse] = Field(default_factory=list)
    rol_permisos: list[RolPermisoAnalyticAdminResponse] = Field(default_factory=list)


class MenuAnalyticAdminTreeResponse(BaseModel):
    id: str
    codigo: str
    label: str
    icon: str | None = None
    id_padre: str | None = None
    tipo: Literal["grupo", "ruta"]
    ruta: str | None = None
    permiso_requerido: str
    orden: int = Field(ge=1)
    activo: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    children: list["MenuAnalyticAdminTreeResponse"] = Field(default_factory=list)


class MenuAnalyticDeleteResponse(BaseModel):
    id: str
    permiso_codigo: str
    rutas_eliminadas: int
    permisos_eliminados: int
    rol_permisos_eliminados: int
    detail: str


MenuAnalyticAdminTreeResponse.model_rebuild()
MenuAnalyticResponse.model_rebuild()

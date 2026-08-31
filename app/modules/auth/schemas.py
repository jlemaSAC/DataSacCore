from datetime import date, datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserLogin(BaseModel):
    codigo: str
    clave: str


class RolOut(BaseModel):
    codigo: str
    nombre: str
    nivel: int
    activo: bool

    model_config = ConfigDict(from_attributes=True)


class OficinaConsultaItem(BaseModel):
    id: int
    nombre: str


class MenuChild(BaseModel):
    label: str
    routerLink: str | None = None
    icon: str | None = None
    children: list["MenuChild"] = Field(default_factory=list)


class LoginResponse(BaseModel):
    puede_ingresar: bool
    nombre: str
    identificacion: str
    codigo: str
    id_agencia: int
    nombre_agencia: str
    activo: bool
    roles: list[RolOut]
    oficinas_consulta: list[OficinaConsultaItem] = Field(default_factory=list)
    token: str
    fecha_sistema: date | datetime


class MenuResponse(BaseModel):
    menu: list[MenuChild] = Field(default_factory=list)


class MenuAdminChild(BaseModel):
    id: str
    codigo: str
    label: str
    icon: str | None = None
    id_padre: str | None = None
    tipo: str
    ruta: str | None = None
    permiso_requerido: str
    orden: int
    activo: bool
    # Roles asignados explicitamente al nodo. Son los unicos que el formulario
    # puede editar; los roles efectivos se calculan a partir del subarbol.
    roles_directos_codigos: list[str] = Field(default_factory=list)
    roles_permitidos_codigos: list[str] = Field(default_factory=list)
    children: list["MenuAdminChild"] = Field(default_factory=list)


class MenuCompleteResponse(BaseModel):
    menu: list[MenuAdminChild] = Field(default_factory=list)


class MenuDataSacWebCreateRequest(BaseModel):
    """Datos administrables de un nodo del menu DataSacWeb.

    El codigo, permiso y ruta se calculan en el servidor a partir de la rama
    elegida. Asi no se pueden crear permisos fuera de la jerarquia del menu.
    """

    label: str = Field(min_length=1, max_length=150)
    icon: str | None = Field(default=None, max_length=100)
    id_padre: str | None = None
    tipo: Literal["grupo", "ruta"] = "grupo"
    orden: int = Field(default=1, ge=1)
    activo: bool = True
    roles_codigo: list[str] = Field(default_factory=lambda: ["001"])


class MenuDataSacWebUpdateRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=150)
    icon: str | None = Field(default=None, max_length=100)
    id_padre: str | None = None
    tipo: Literal["grupo", "ruta"] | None = None
    orden: int | None = Field(default=None, ge=1)
    activo: bool | None = None
    # Una lista enviada (tambien vacia) reemplaza por completo la asignacion
    # directa del nodo. Los permisos de sus ancestros se recalculan despues.
    roles_codigo: list[str] | None = None


class MenuDataSacWebDeleteResponse(BaseModel):
    id: str
    permiso_codigo: str
    detail: str


class UsuarioTokenPayload(BaseModel):
    sub: str
    usuario: str
    id_agencia: int
    nombre_agencia: str = ""
    fecha_sistema: date | datetime

    @field_validator("fecha_sistema", mode="before")
    @classmethod
    def parse_fecha_sistema(cls, value: object) -> object:
        if isinstance(value, str):
            if "T" not in value and " " not in value:
                return date.fromisoformat(value)
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return date.fromisoformat(value)
        return value

    model_config = ConfigDict(from_attributes=True)


class AuthContext(BaseModel):
    usuario: UsuarioTokenPayload
    token: str

    @classmethod
    def from_token_payload(cls, token: str, payload: UsuarioTokenPayload) -> "AuthContext":
        return cls(usuario=payload, token=token)


MenuAdminChild.model_rebuild()

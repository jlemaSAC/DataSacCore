from datetime import date, datetime

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
    menu: list[MenuChild] = Field(default_factory=list)
    token: str
    fecha_sistema: date | datetime


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

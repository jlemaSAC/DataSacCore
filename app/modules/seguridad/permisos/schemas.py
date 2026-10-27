from pydantic import BaseModel, ConfigDict, Field

from app.modules.auth.schemas import MenuAdminChild
from app.modules.seguridad.roles.schemas import RolResponse


class AccessChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    menu_id: str = Field(min_length=1)
    rol_codigo: str = Field(min_length=1)
    conceder: bool


class AccessBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=64, max_length=64)
    cambios: list[AccessChange] = Field(min_length=1, max_length=50000)


class AccessSnapshot(BaseModel):
    version: str
    menu: list[MenuAdminChild]


class AccessStateResponse(AccessSnapshot):
    cargos: list[RolResponse]


class AccessBatchResponse(AccessStateResponse):
    modificaciones: int
    detail: str = "Permisos guardados correctamente."

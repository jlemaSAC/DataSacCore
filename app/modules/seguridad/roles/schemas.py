from pydantic import BaseModel, ConfigDict


class RolResponse(BaseModel):
    codigo: str
    nombre: str
    nivel: int
    activo: bool

    model_config = ConfigDict(from_attributes=True)

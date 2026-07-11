from pydantic import BaseModel, ConfigDict


class CargoResponse(BaseModel):
    id: int
    nombre: str
    activo: bool
    es_vinculado: bool | None = None

    model_config = ConfigDict(from_attributes=True)

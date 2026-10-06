from datetime import date

from pydantic import BaseModel, Field

from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.schemas import (
    AsesorCarteraComparativo,
    ResumenCarteraComparativo,
)
from app.modules.negocios.colocacion.diaria_asesores.schemas import (
    ColocacionAsesorComparativo,
    ColocacionResumenComparativo,
)


class InicioColocacion(BaseModel):
    resumen: ColocacionResumenComparativo
    asesores: list[ColocacionAsesorComparativo] = Field(default_factory=list)


class InicioCarteraCredito(BaseModel):
    resumen: ResumenCarteraComparativo
    asesores: list[AsesorCarteraComparativo] = Field(default_factory=list)


class NegocioInicioResponse(BaseModel):
    fecha: date
    fecha_ayer: date
    id_agencia: int
    agencia: str
    colocacion: InicioColocacion
    cartera_de_credito: InicioCarteraCredito

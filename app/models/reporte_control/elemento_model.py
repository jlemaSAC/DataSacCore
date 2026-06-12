from pydantic import BaseModel
from typing import List, Optional

class ElementoType(BaseModel):
    tipoIdentificacion: str
    numeroIdentificacion: str
    apellidosNombres: str
    fechaNacimiento: Optional[str]
    paisNacimiento: Optional[str]
    genero: str
    valorCertifAportacion: float
    fechaIngreso: str
    asambleaGeneral: Optional[str]
    fechaRepresentanteAsamblea: Optional[str]
    directivo: Optional[str]
    fechaDirectivo: Optional[str]

class SocioType(BaseModel):
    rucEntidad: str
    estructura: str
    fechaCorte: str
    numRegistro: str
    elemento: List[ElementoType]
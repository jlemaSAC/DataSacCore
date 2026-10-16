from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InputDepositosCastigo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_desde: date = Field(description="Primera fecha de depósito incluida.")
    fecha_hasta: date = Field(description="Última fecha de depósito incluida.")
    agencias: list[str] = Field(default_factory=list, max_length=500)
    asesores: list[str] = Field(default_factory=list, max_length=500)
    cargos: list[str] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def validar_rango(self) -> "InputDepositosCastigo":
        if self.fecha_hasta < self.fecha_desde:
            raise ValueError("fecha_hasta no puede ser menor que fecha_desde.")
        return self

    @field_validator("agencias", "asesores", "cargos", mode="after")
    @classmethod
    def normalizar_filtros(cls, valores: list[str]) -> list[str]:
        normalizados: list[str] = []
        vistos: set[str] = set()
        for valor in valores:
            texto = valor.strip().upper()
            if texto and texto not in vistos:
                vistos.add(texto)
                normalizados.append(texto)
        return normalizados


class DepositoCastigoDiarioOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    numero_prestamo: str = Field(alias="NumeroPrestamo")
    fecha: date = Field(alias="Fecha")
    estado_inicio: str = Field(alias="EstadoPrestamoInicio")
    estado_fin: str = Field(alias="EstadoPrestamoFin")
    tipo_transaccion: str = Field(alias="TipoTransaccion")
    agencia: str = Field(alias="Agencia")
    codigo_asesor: str = Field(alias="CodigoAsesor")
    asesor: str = Field(alias="Asesor")
    cargo_asesor: str = Field(alias="CargoAsesor")
    total_depositado: float = Field(alias="TotalDepositado")


class DepositosCastigoCatalogosOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agencias: list[str] = Field(alias="Agencias")
    asesores: list[str] = Field(alias="Asesores")
    cargos: list[str] = Field(alias="Cargos")


class DepositosCastigoResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fecha_desde: date = Field(alias="FechaDesde")
    fecha_hasta: date = Field(alias="FechaHasta")
    depositos: list[DepositoCastigoDiarioOut] = Field(alias="Depositos")
    total_depositado: float = Field(alias="TotalDepositado")
    catalogos: DepositosCastigoCatalogosOut = Field(alias="Catalogos")

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.schemas import (
    SituacionCrediticiaAgenciaGerenteItem,
)


class CarteraImproductivaRequest(BaseModel):
    fecha_inicio: date = Field(description="Fecha inicial del rango.")
    fecha_fin: date = Field(description="Fecha final del rango.")
    id_agencia: int = Field(default=0, ge=0, description="0 para consolidado.")
    filtrar_diferidos: bool | None = Field(default=None)


class CarteraImproductivaMorosidadValores(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    saldo_capital: float = Field(alias="SaldoCapital")
    cartera_improductiva: float = Field(alias="CarteraImproductiva")
    morosidad: float = Field(
        alias="Morosidad",
        description="Índice de morosidad en escala decimal.",
    )
    morosidad_porcentaje: float = Field(alias="MorosidadPorcentaje")


class CarteraImproductivaComparacionAsesor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    codigo_usuario: str = Field(alias="CodigoUsuario")
    nombre_asesor_fecha_fin: str | None = Field(
        default=None,
        alias="NombreAsesorFechaFin",
    )
    nombre_asesor_fecha_inicio: str | None = Field(
        default=None,
        alias="NombreAsesorFechaInicio",
    )
    nombre_asesor_dia_anterior_fecha_fin: str | None = Field(
        default=None,
        alias="NombreAsesorDiaAnteriorFechaFin",
    )
    cargo_asesor_fecha_fin: str | None = Field(
        default=None,
        alias="CargoAsesorFechaFin",
    )
    agencia_fecha_fin: str | None = Field(default=None, alias="AgenciaFechaFin")
    agencia_fecha_inicio: str | None = Field(
        default=None,
        alias="AgenciaFechaInicio",
    )
    agencia_dia_anterior_fecha_fin: str | None = Field(
        default=None,
        alias="AgenciaDiaAnteriorFechaFin",
    )
    valores_fecha_fin: CarteraImproductivaMorosidadValores | None = Field(
        default=None,
        alias="ValoresFechaFin",
    )
    valores_fecha_inicio: CarteraImproductivaMorosidadValores | None = Field(
        default=None,
        alias="ValoresFechaInicio",
    )
    valores_dia_anterior_fecha_fin: (
        CarteraImproductivaMorosidadValores | None
    ) = Field(
        default=None,
        alias="ValoresDiaAnteriorFechaFin",
    )


class CarteraImproductivaResponse(BaseModel):
    fecha_corte_fecha_fin: str
    fecha_corte_fecha_inicio: str
    fecha_corte_dia_anterior_fecha_fin: str
    comparacion: list[CarteraImproductivaComparacionAsesor]
    agencias_gerentes_oficina: list[SituacionCrediticiaAgenciaGerenteItem]
    faltantes_en_fecha_fin: list[str]
    faltantes_en_fecha_inicio: list[str]
    faltantes_en_dia_anterior_fecha_fin: list[str]


class CarteraImproductivaGrupo(BaseModel):
    codigo_usuario: str = Field(min_length=1)
    agencia: str | None = None


class CarteraImproductivaPrestamosRequest(CarteraImproductivaRequest):
    grupos: list[CarteraImproductivaGrupo] = Field(min_length=1)
    solo_improductivos: bool = False
    orden_por: str = Field(
        default="ValoresFechaFin__CarteraImproductiva",
        pattern=(
            r"^(numero_prestamo|nombre_cliente|nombre|agencia|"
            r"variacionDiaAnterior|variacionCartera|"
            r"variacionMorosidadDiaAnterior|variacionMorosidadCartera|"
            r"Valores(FechaInicio|FechaFin|DiaAnteriorFechaFin)__"
            r"(CarteraImproductiva|MorosidadPorcentaje))$"
        ),
    )
    orden: Literal[1, -1] = -1


class CarteraImproductivaPrestamo(CarteraImproductivaComparacionAsesor):
    numero_prestamo: str = Field(alias="NumeroPrestamo")
    nombre_cliente: str | None = Field(default=None, alias="NombreCliente")
    numero_socio: str | None = Field(default=None, alias="NumeroSocio")


class CarteraImproductivaPrestamosResponse(BaseModel):
    fecha_corte_fecha_fin: str
    fecha_corte_fecha_inicio: str
    fecha_corte_dia_anterior_fecha_fin: str
    prestamos: list[CarteraImproductivaPrestamo]
    totales: CarteraImproductivaComparacionAsesor
    total_seleccion: int
    total_resultados: int

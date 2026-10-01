from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class SituacionCrediticiaAsesoresRequest(BaseModel):
    fecha_inicio: date = Field(description="Fecha inicial del corte.")
    fecha_fin: date = Field(description="Fecha final del corte.")
    id_agencia: int = Field(default=0, ge=0, description="0 para consolidado.")
    filtrar_diferidos: bool | None = Field(default=None)


class SituacionCrediticiaAsesorValores(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    operaciones: int = Field(alias="Operaciones")
    clientes: int = Field(alias="Clientes")
    saldo_capital: float = Field(alias="SaldoCapital")
    capital_vigente: float = Field(alias="CapitalVigente")
    capital_no_devenga: float = Field(alias="CapitalNoDevenga")
    capital_vencido: float = Field(alias="CapitalVencido")
    provision_requerida: float = Field(alias="ProvisionRequerida")
    cartera_improductiva: float = Field(alias="CarteraImproductiva")
    mora: float = Field(alias="Mora")
    mora_porcentaje: float = Field(alias="MoraPorcentaje")


class SituacionCrediticiaAsesorComparacion(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    codigo_usuario: str = Field(alias="CodigoUsuario")
    nombre_asesor_actual: str | None = Field(
        default=None,
        alias="NombreAsesorActual",
    )
    cargo_asesor_actual: str | None = Field(
        default=None,
        alias="CargoAsesorActual",
    )
    nombre_asesor_cierre_mes_anterior: str | None = Field(
        default=None,
        alias="NombreAsesorCierreMesAnterior",
    )
    agencia_actual: str | None = Field(default=None, alias="AgenciaActual")
    agencia_cierre_mes_anterior: str | None = Field(
        default=None,
        alias="AgenciaCierreMesAnterior",
    )
    valores_actual: SituacionCrediticiaAsesorValores | None = Field(
        default=None,
        alias="ValoresActual",
    )
    valores_cierre_mes_anterior: SituacionCrediticiaAsesorValores | None = Field(
        default=None,
        alias="ValoresCierreMesAnterior",
    )
    diferencias_cierre_mes_anterior: SituacionCrediticiaAsesorValores | None = Field(
        default=None,
        alias="DiferenciasCierreMesAnterior",
    )


class SituacionCrediticiaAgenciaGerenteItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id_agencia: int | None = Field(default=None, alias="IdAgencia")
    agencia: str = Field(alias="Agencia")
    codigo_usuario_gerente: str | None = Field(
        default=None,
        alias="CodigoUsuarioGerente",
    )
    gerente_oficina: str | None = Field(default=None, alias="GerenteOficina")
    cargo: str | None = Field(default=None, alias="Cargo")


class SituacionCrediticiaAsesoresResponse(BaseModel):
    fecha_corte_actual: str
    fecha_corte_cierre_mes_anterior: str
    comparacion: list[SituacionCrediticiaAsesorComparacion]
    agencias_gerentes_oficina: list[SituacionCrediticiaAgenciaGerenteItem]
    faltantes_en_cierre_mes_anterior: list[str]
    faltantes_en_actual: list[str]

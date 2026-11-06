from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.schemas import (
    SituacionCrediticiaAgenciaGerenteItem,
)


class EvaluacionCuentasAhorroVistaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date
    fecha_fin: date
    id_agencia: int = Field(default=0, ge=0, description="0 para consolidado.")

    @model_validator(mode="after")
    def validar_rango(self) -> "EvaluacionCuentasAhorroVistaRequest":
        if self.fecha_inicio > self.fecha_fin:
            raise ValueError("fecha_inicio no puede ser posterior a fecha_fin.")
        if self.fecha_inicio.replace(day=1) != self.fecha_fin.replace(day=1):
            raise ValueError("fecha_inicio y fecha_fin deben pertenecer al mismo mes.")
        return self


class CuentaAhorroVistaVariacion(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    saldo: float = Field(alias="Saldo")
    cuentas: int = Field(alias="Cuentas")
    tasa_promedio: float | None = Field(alias="TasaPromedio")


class CuentaAhorroVistaValores(CuentaAhorroVistaVariacion):
    cuentas: int = Field(alias="Cuentas", ge=0)
    suma_tasas: float = Field(
        alias="SumaTasas",
        description="Sumar y dividir por Cuentas para reagrupar la tasa sin promediar promedios.",
    )


class CuentaAhorroVistaComparacion(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    clave: str = Field(alias="Clave", description="Usuario::agencia::tipo de cuenta.")
    codigo_usuario: str = Field(alias="CodigoUsuario")
    id_agencia: int = Field(alias="IdAgencia")
    codigo_producto: str = Field(alias="CodigoProducto", description="TIPO_CUENTA.CODIGO.")
    producto_ahorro: str = Field(alias="ProductoAhorro")
    nombre_asesor_actual: str | None = Field(alias="NombreAsesorActual")
    nombre_asesor_cierre_mes_anterior: str | None = Field(alias="NombreAsesorCierreMesAnterior")
    agencia_actual: str | None = Field(alias="AgenciaActual")
    agencia_cierre_mes_anterior: str | None = Field(alias="AgenciaCierreMesAnterior")
    valores_actual: CuentaAhorroVistaValores | None = Field(alias="ValoresActual")
    valores_cierre_mes_anterior: CuentaAhorroVistaValores | None = Field(alias="ValoresCierreMesAnterior")
    diferencias_cierre_mes_anterior: CuentaAhorroVistaVariacion = Field(alias="DiferenciasCierreMesAnterior")


class EvaluacionCuentasAhorroVistaResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    fecha_corte_actual: date
    fecha_corte_cierre_mes_anterior: date
    comparacion: list[CuentaAhorroVistaComparacion]
    agencias_gerentes_oficina: list[SituacionCrediticiaAgenciaGerenteItem]
    faltantes_en_cierre_mes_anterior: list[str]
    faltantes_en_actual: list[str]

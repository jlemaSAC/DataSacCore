from datetime import date

from pydantic import BaseModel, Field, model_validator


class InputSaldoInicialAgencia(BaseModel):
    anio: int = Field(
        ge=1900,
        examples=[2026],
        description="Año de adjudicación que se desea consultar.",
    )


class InputColocacionHistoricoRango(BaseModel):
    fecha_desde: date = Field(
        examples=["2025-12-15"],
        description="Primera fecha de adjudicación incluida.",
    )
    fecha_hasta: date = Field(
        examples=["2026-02-10"],
        description="Última fecha de adjudicación incluida.",
    )

    @model_validator(mode="after")
    def validar_rango(self) -> "InputColocacionHistoricoRango":
        if self.fecha_hasta < self.fecha_desde:
            raise ValueError("fecha_hasta no puede ser menor que fecha_desde.")
        return self


class ResumenMensualColocacion(BaseModel):
    periodo: str = Field(description="Período en formato YYYY-MM.")
    anio: int = Field(description="Año del período.")
    mes: int = Field(description="Número del mes, de 1 a 12.")
    operaciones: int = Field(description="Cantidad de préstamos adjudicados en el mes.")
    saldo_inicial: float = Field(description="Suma de DeudaInicial adjudicada en el mes.")


class ColocacionHistoricoAgrupacion(BaseModel):
    periodo: str = Field(description="Período en formato YYYY-MM.")
    anio: int = Field(description="Año de la agrupación.")
    mes: int = Field(description="Número del mes de la agrupación.")
    agencia: str = Field(description="Agencia de adjudicación.")
    condicion: str = Field(description="Condición de emisión del préstamo.")
    tipo_prestamo: str = Field(description="Tipo de préstamo.")
    producto: str = Field(description="Calificación contable o producto.")
    segmento: str = Field(description="Subcalificación contable o segmento.")
    asesor: str = Field(description="Nombre del asesor; usa el código como respaldo.")
    provincia: str = Field(description="Provincia de residencia del cliente.")
    canton: str = Field(description="Cantón de residencia del cliente.")
    parroquia: str = Field(description="Parroquia de residencia del cliente.")
    educacion: str = Field(description="Nivel de educación del cliente.")
    edad: str = Field(description="Rango de edad: HASTA 20, HASTA 30, ..., MAS DE 100.")
    garantia: str = Field(description="Tipo principal de garantía del préstamo.")
    monto: str = Field(description="Rango del monto inicial del préstamo.")
    tasa: str = Field(description="Rango de la tasa del préstamo.")
    plazo: str = Field(description="Rango del plazo original del préstamo.")
    operaciones: int = Field(description="Préstamos representados por esta agrupación.")
    saldo_inicial: float = Field(description="Suma de DeudaInicial de la agrupación.")


class SaldoInicialAgenciaResponse(BaseModel):
    anio: int = Field(description="Año consultado.")
    total_operaciones: int = Field(description="Total anual de préstamos adjudicados.")
    total_saldo_inicial: float = Field(description="Suma anual de DeudaInicial.")
    resumen_mensual: list[ResumenMensualColocacion] = Field(
        description="Doce elementos, uno por mes, incluyendo meses sin movimientos."
    )
    agrupaciones: list[ColocacionHistoricoAgrupacion] = Field(
        description="Tabla de hechos agregada para filtros y visualizaciones del dashboard."
    )


class ResumenRangoColocacion(BaseModel):
    periodo: str = Field(description="Período en formato YYYY-MM.")
    anio: int
    mes: int
    fecha_desde: date = Field(description="Inicio efectivo del segmento mensual.")
    fecha_hasta: date = Field(description="Fin efectivo del segmento mensual.")
    operaciones: int
    saldo_inicial: float


class ColocacionHistoricoRangoResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    total_operaciones: int
    total_saldo_inicial: float
    resumen_mensual: list[ResumenRangoColocacion]
    agrupaciones: list[ColocacionHistoricoAgrupacion]

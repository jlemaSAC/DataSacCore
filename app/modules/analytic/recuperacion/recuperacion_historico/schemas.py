from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RecuperacionDimension = Literal[
    "agencia",
    "asesor",
    "tipo_prestamo",
    "condicion",
    "producto",
    "segmento",
    "provincia",
    "canton",
    "parroquia",
    "educacion",
    "edad",
    "garantia",
    "monto",
    "tasa",
    "tasa_real",
    "plazo",
    "tipo_cobro",
    "tipo_transaccion",
    "abogado_externo",
    "nombre_cobranza_apoyo",
    "estado_prestamo_anterior_cobro",
    "calificacion_anterior_cobro",
    "estado_prestamo_actual_cobro",
    "calificacion_actual_cobro",
]


class InputRecuperacionHistoricoRango(BaseModel):
    """Rango de recuperación; la fuente de consulta es solo MongoDB."""

    model_config = ConfigDict(extra="forbid")

    fecha_desde: date = Field(description="Primera fecha de cobro incluida.")
    fecha_hasta: date = Field(description="Última fecha de cobro incluida.")

    @model_validator(mode="after")
    def validar_rango(self) -> "InputRecuperacionHistoricoRango":
        if self.fecha_hasta < self.fecha_desde:
            raise ValueError("fecha_hasta no puede ser menor que fecha_desde.")
        return self


class RecuperacionEtiquetadaOut(BaseModel):
    anio: int
    mes: int
    numero_prestamo: str
    tipo_cobro: str
    tipo_transaccion: str
    valor_recuperado: float
    agencia: str
    asesor: str
    abogado_externo: str
    nombre_cobranza_apoyo: str
    estado_prestamo_anterior_cobro: str
    estado_prestamo_actual_cobro: str
    calificacion_anterior_cobro: str
    calificacion_actual_cobro: str
    se_cancelo_con_el_cobro: bool


class PrestamoRecuperacionOut(BaseModel):
    numero_prestamo: str
    agencia: str
    condicion: str
    tipo_prestamo: str
    producto: str
    segmento: str
    asesor: str
    provincia: str
    canton: str
    parroquia: str
    educacion: str
    edad: int | None
    garantia: str
    monto: float | None = Field(description="Deuda inicial del préstamo en el corte final.")
    tasa: float | None = Field(description="Tasa nominal en el corte final.")
    tasa_real: float | None = Field(description="Tasa anual en el corte final.")
    plazo: int | None = Field(description="Plazo registrado en el corte final.")
    estado_prestamo_inicio: str
    estado_prestamo_fin: str
    calificacion_inicio: str = "SIN DATOS"
    calificacion_fin: str = "SIN DATOS"


class RecuperacionHistoricoRangoResponse(BaseModel):
    prestamos_por_numero: dict[str, PrestamoRecuperacionOut]
    recuperaciones: list[RecuperacionEtiquetadaOut]


CAMPOS_PRESTAMO_COMPACTO = (
    "numero_prestamo",
    "agencia_id",
    "condicion_id",
    "tipo_prestamo_id",
    "producto_id",
    "segmento_id",
    "asesor_id",
    "provincia_id",
    "canton_id",
    "parroquia_id",
    "educacion_id",
    "edad",
    "garantia_id",
    "monto_centavos",
    "tasa_centenas",
    "tasa_real_centenas",
    "plazo_meses",
    "estado_inicio_id",
    "estado_fin_id",
    "calificacion_inicio_id",
    "calificacion_fin_id",
)
CAMPOS_RECUPERACION_COMPACTO = (
    "periodo_id",
    "prestamo_id",
    "tipo_cobro_id",
    "tipo_transaccion_id",
    "valor_centavos",
    "agencia_id",
    "asesor_id",
    "abogado_externo_id",
    "nombre_cobranza_apoyo_id",
    "estado_anterior_id",
    "estado_actual_id",
    "calificacion_anterior_id",
    "calificacion_actual_id",
    "se_cancelo_con_el_cobro",
)


class RecuperacionCatalogosCompactosOut(BaseModel):
    agencias: list[str]
    condiciones: list[str]
    tipos_prestamo: list[str]
    productos: list[str]
    segmentos: list[str]
    asesores: list[str]
    provincias: list[str]
    cantones: list[str]
    parroquias: list[str]
    educaciones: list[str]
    garantias: list[str]
    estados_prestamo: list[str]
    calificaciones: list[str]
    tipos_cobro: list[str]
    tipos_transaccion: list[str]
    abogados_externos: list[str]
    nombres_cobranza_apoyo: list[str]


class RecuperacionResumenCompactoOut(BaseModel):
    cantidad_prestamos: int
    cantidad_recuperaciones: int


class RecuperacionHistoricoCompactoResponse(BaseModel):
    formato: Literal["recuperacion-compacta-v2"] = "recuperacion-compacta-v2"
    esquema_prestamos: list[str] = Field(default_factory=lambda: list(CAMPOS_PRESTAMO_COMPACTO))
    esquema_recuperaciones: list[str] = Field(
        default_factory=lambda: list(CAMPOS_RECUPERACION_COMPACTO)
    )
    periodos: list[str]
    catalogos: RecuperacionCatalogosCompactosOut
    prestamos: list[list[str | int]]
    recuperaciones: list[list[int]]
    resumen: RecuperacionResumenCompactoOut


class InputRecuperacionHistoricoAgrupado(InputRecuperacionHistoricoRango):
    """Consulta agregada; los filtros se aplican antes de construir las series."""

    dimension: RecuperacionDimension
    agencias: list[str] = Field(default_factory=list, max_length=500)
    asesores: list[str] = Field(default_factory=list, max_length=500)
    tipos_prestamo: list[str] = Field(default_factory=list, max_length=500)

    @field_validator("agencias", "asesores", "tipos_prestamo", mode="after")
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


class RecuperacionPeriodoOut(BaseModel):
    clave: str
    anio: int
    mes: int
    etiqueta: str


class RecuperacionSerieOut(BaseModel):
    clave: str
    etiqueta: str
    valores: list[float]
    total: float


class RecuperacionCatalogosOut(BaseModel):
    agencias: list[str]
    asesores: list[str]
    tipos_prestamo: list[str]


class RecuperacionResumenAgrupadoOut(BaseModel):
    cantidad_movimientos: int
    cantidad_series: int


class RecuperacionHistoricoAgrupadoResponse(BaseModel):
    dimension: RecuperacionDimension
    periodos: list[RecuperacionPeriodoOut]
    series: list[RecuperacionSerieOut]
    totales_por_periodo: list[float]
    total_general: float
    catalogos: RecuperacionCatalogosOut
    resumen: RecuperacionResumenAgrupadoOut

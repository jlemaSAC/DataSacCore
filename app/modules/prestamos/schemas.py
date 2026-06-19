from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class PrestamoUniverseRequest(BaseModel):
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    fecha_corte_anterior: datetime | None = None
    fecha_corte_actual: datetime | None = None

    ids_prestamo: list[int] = Field(default_factory=list)
    numeros_prestamo: list[str] = Field(default_factory=list)

    agencias: list[int] = Field(default_factory=list)
    agencia_nombres: list[str] = Field(default_factory=list)

    codigos_asesor: list[str] = Field(default_factory=list)
    codigos_usuario_control: list[str] = Field(default_factory=list)
    codigos_usuario_cobranza_apoyo: list[str] = Field(default_factory=list)
    ids_cargo_asesor: list[int] = Field(default_factory=list)

    estados_prestamo: list[str] = Field(default_factory=list)
    calificaciones: list[str] = Field(default_factory=list)
    productos: list[str] = Field(default_factory=list)
    tipos_prestamo: list[str] = Field(default_factory=list)
    provincias: list[str] = Field(default_factory=list)

    filtrar_diferidos: bool | None = None
    excluir_cancelados: bool = True
    incluir_cancelados_periodo: bool = False

    aplicar_filtros_en: Literal["actual", "historico", "ambos"] = "actual"


class PrestamoSnapshot(BaseModel):
    id_prestamo: int | None = None
    numero_prestamo: str

    id_agencia: int | None = None
    agencia: str | None = None

    codigo_estado_prestamo: str | None = None
    estado_prestamo: str | None = None
    es_cancelado: bool = False
    es_diferido: bool = False

    codigo_asesor: str | None = None
    nombre_asesor: str | None = None
    id_cargo_asesor: int | None = None
    cargo_asesor: str | None = None

    codigo_usuario_control: str | None = None
    usuario_control: str | None = None
    codigo_usuario_cobranza_apoyo: str | None = None
    cobranza_apoyo: str | None = None

    calificacion: str | None = None
    dias_vencidos: int = 0
    producto: str | None = None
    tipo_prestamo: str | None = None
    provincia: str | None = None

    saldo_capital: float = 0.0
    capital_vigente: float = 0.0
    capital_no_devenga: float = 0.0
    capital_vencido: float = 0.0
    provision_requerida: float = 0.0
    provision_requerida_fuente: float = 0.0
    provision_requerida_calculada: float = 0.0
    provision_constituida: float = 0.0
    porcentaje_provision_aplicado: float = 0.0
    porcentaje_provision_fuente: float = 0.0
    porcentaje_provision_minimo: float = 0.0
    porcentaje_provision_maximo: float = 0.0
    es_porcentaje_fijo: bool = False
    provision_diferencia_validacion: float = 0.0

    exigible_capital: float = 0.0
    exigible_interes: float = 0.0
    exigible_mora: float = 0.0
    exigible_otros: float = 0.0
    valor_para_estar_al_dia: float = 0.0
    valor_hasta_cuota_actual: float = 0.0
    valor_cancelar_total: float = 0.0

    data_version: str | None = None


class CarteraMetricas(BaseModel):
    operaciones: int = 0
    saldo_capital: float = 0.0
    capital_vigente: float = 0.0
    capital_no_devenga: float = 0.0
    capital_vencido: float = 0.0
    cartera_improductiva: float = 0.0
    mora: float = 0.0
    mora_porcentaje: float = 0.0
    provision_requerida: float = 0.0
    provision_constituida: float = 0.0


class UniversoPrestamosConteos(BaseModel):
    actual: int = 0
    historico: int = 0


class UniversoPrestamosBuscarResponse(BaseModel):
    actual: list[PrestamoSnapshot] = Field(default_factory=list)
    historico: list[PrestamoSnapshot] = Field(default_factory=list)
    conteos: UniversoPrestamosConteos


class SituacionCrediticiaActualSyncRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1)
    confirmar_carga_total: bool = False

    @model_validator(mode="after")
    def validar_carga_total(self) -> "SituacionCrediticiaActualSyncRequest":
        if self.limit is None and not self.confirmar_carga_total:
            raise ValueError("Enviar limit para pruebas o confirmar_carga_total=true para una carga completa.")
        return self


class SituacionCrediticiaActualSyncTimings(BaseModel):
    ensure_indexes_ms: float
    sql_read_ms: float
    python_map_ms: float
    mongo_upsert_ms: float
    total_ms: float


class SituacionCrediticiaActualSyncResponse(BaseModel):
    collection: str
    data_version: str
    as_of: datetime
    total_leidos_sql: int
    total_upserted: int
    total_matched: int
    total_modified: int
    total_sin_cambios: int = 0
    timings_ms: SituacionCrediticiaActualSyncTimings

    @field_validator("data_version")
    @classmethod
    def validar_data_version(cls, data_version: str) -> str:
        if not data_version.strip():
            raise ValueError("data_version no puede estar vacio.")
        return data_version

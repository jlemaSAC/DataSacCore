from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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
    producto: str | None = None
    tipo_prestamo: str | None = None
    provincia: str | None = None

    saldo_capital: float = 0.0
    capital_vigente: float = 0.0
    capital_no_devenga: float = 0.0
    capital_vencido: float = 0.0
    provision_requerida: float = 0.0
    provision_constituida: float = 0.0

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


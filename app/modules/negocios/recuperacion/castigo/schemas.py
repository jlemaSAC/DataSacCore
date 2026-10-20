from datetime import date, datetime

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
        if (self.fecha_desde.year, self.fecha_desde.month) != (
            self.fecha_hasta.year, self.fecha_hasta.month
        ):
            raise ValueError("fecha_desde y fecha_hasta deben pertenecer al mismo mes.")
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
    tipo_transaccion: str = Field(
        alias="TipoTransaccion",
        description="Origen del importe diario: VARIACION DEPOSITOS MES; no representa una transacción individual.",
    )
    agencia: str = Field(alias="Agencia")
    codigo_asesor: str = Field(alias="CodigoAsesor")
    asesor: str = Field(alias="Asesor")
    cargo_asesor: str = Field(alias="CargoAsesor")
    total_depositado: float = Field(
        alias="TotalDepositado",
        description="Diferencia de DepositosMes respecto al día anterior, con base cero al comenzar el mes.",
    )


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


class InputDetalleDepositosCastigo(InputDepositosCastigo):
    numeros_prestamo: list[str] = Field(min_length=1, max_length=5000)
    fecha_deposito: date | None = None
    pagina: int = Field(default=1, ge=1)
    tamano_pagina: int = Field(default=50, ge=1, le=100)
    incluir_movimientos: bool = True

    @field_validator("numeros_prestamo")
    @classmethod
    def validar_numeros(cls, valores: list[str]) -> list[str]:
        numeros = list(dict.fromkeys(valor.strip() for valor in valores if valor.strip()))
        if not numeros or any(len(numero) > 100 for numero in numeros):
            raise ValueError("Indica números de préstamo válidos.")
        return numeros

    @model_validator(mode="after")
    def validar_fecha_deposito(self) -> "InputDetalleDepositosCastigo":
        if self.fecha_deposito and not self.fecha_desde <= self.fecha_deposito <= self.fecha_hasta:
            raise ValueError("fecha_deposito debe estar dentro del rango consultado.")
        return self


class MovimientoDepositoCuentaOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id_detalle: int = Field(alias="IdDetalle")
    id_movimiento: int = Field(alias="IdMovimiento")
    fecha_sistema: datetime = Field(alias="FechaSistema")
    fecha_proceso: datetime | None = Field(alias="FechaProceso")
    cliente: int = Field(alias="Cliente")
    nombre_cliente: str = Field(alias="NombreCliente")
    numero_cuenta: str = Field(alias="NumeroCuenta")
    documento: str = Field(alias="Documento")
    tipo_transaccion: str = Field(alias="TipoTransaccion")
    detalle: str = Field(alias="Detalle")
    valor: float = Field(alias="Valor")
    es_reverso: bool = Field(alias="EsReverso")
    prestamos_relacionados: str = Field(alias="PrestamosRelacionados")


class DetalleDepositosCastigoResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fecha_desde: date = Field(alias="FechaDesde")
    fecha_hasta: date = Field(alias="FechaHasta")
    depositos: list[DepositoCastigoDiarioOut] = Field(alias="Depositos")
    total_depositado: float = Field(alias="TotalDepositado")
    movimientos: list[MovimientoDepositoCuentaOut] = Field(alias="Movimientos")
    total_movimientos: int = Field(alias="TotalMovimientos")
    total_creditos_cuenta: float = Field(alias="TotalCreditosCuenta")
    pagina: int = Field(alias="Pagina")
    tamano_pagina: int = Field(alias="TamanoPagina")

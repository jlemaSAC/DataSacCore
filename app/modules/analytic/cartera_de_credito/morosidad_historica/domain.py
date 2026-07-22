from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class DimensionesMorosidad:
    periodo: str
    anio: int
    mes: int
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
    edad: str
    garantia: str
    monto: str
    tasa: str
    tasa_valor: float | None
    tasa_real: str
    tasa_real_valor: float | None
    plazo: str
    plazo_valor: int | None


@dataclass
class MorosidadAgrupada:
    dimensiones: DimensionesMorosidad
    operaciones: int
    saldo_capital: float
    capital_vigente: float
    capital_no_devenga: float
    capital_vencido: float

    @property
    def cartera_improductiva(self) -> float:
        return self.capital_no_devenga + self.capital_vencido

    @property
    def morosidad(self) -> float:
        if self.saldo_capital == 0:
            return 0.0
        return self.cartera_improductiva / self.saldo_capital


from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TotalesCartera:
    fecha_corte: date
    operaciones: int
    saldo_capital: float
    capital_vigente: float
    capital_no_devenga: float
    capital_vencido: float
    provision_requerida: float

    @property
    def cartera_improductiva(self) -> float:
        return self.capital_no_devenga + self.capital_vencido

    @property
    def morosidad(self) -> float:
        if not self.saldo_capital:
            return 0.0
        return self.cartera_improductiva / self.saldo_capital

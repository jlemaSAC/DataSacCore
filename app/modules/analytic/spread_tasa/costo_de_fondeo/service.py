from app.modules.analytic.indicadores_financieros.fechas_historicas import fecha_actual_ecuador
from app.modules.analytic.spread_tasa.calculos import TIPOS_COSTO, componentes_costos
from app.modules.analytic.spread_tasa.historico import consultar_historico
from .schemas import CostoFondeoInput, CostoFondeoResponse


class CostoFondeoService:
    def __init__(self, repository):
        self.repository = repository

    def consultar(self, consulta: CostoFondeoInput) -> CostoFondeoResponse:
        return CostoFondeoResponse(**consultar_historico(
            self.repository, consulta, hoy=fecha_actual_ecuador(),
            definiciones=TIPOS_COSTO, calcular_componentes=componentes_costos,
            campo_tipo='tipo_costo', campo_valor='costo',
        ))

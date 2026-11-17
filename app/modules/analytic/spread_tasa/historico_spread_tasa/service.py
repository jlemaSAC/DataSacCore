from app.modules.analytic.indicadores_financieros.fechas_historicas import fecha_actual_ecuador
from app.modules.analytic.spread_tasa.calculos import INDICADORES_SPREAD, componentes_spread
from app.modules.analytic.spread_tasa.historico import consultar_historico
from .schemas import HistoricoSpreadTasaInput, HistoricoSpreadTasaResponse


class HistoricoSpreadTasaService:
    def __init__(self, repository):
        self.repository = repository

    def consultar(self, consulta: HistoricoSpreadTasaInput) -> HistoricoSpreadTasaResponse:
        resultado = consultar_historico(
            self.repository, consulta, hoy=fecha_actual_ecuador(),
            definiciones=INDICADORES_SPREAD, calcular_componentes=componentes_spread,
            campo_tipo='indicador', campo_valor='valor',
        )
        for dato in resultado['datos']:
            if dato['indicador'] == 'spread_tasa':
                dato.setdefault('componentes', {
                    'rendimiento_cartera_por_vencer': {}, 'costo_promedio_fondeo': {},
                })
        return HistoricoSpreadTasaResponse(**resultado)

from app.modules.analytic.indicadores_financieros.fechas_historicas import fecha_actual_ecuador
from app.modules.analytic.spread_tasa.calculos import PRODUCTOS_RENDIMIENTO, componentes_rendimientos
from app.modules.analytic.spread_tasa.historico import consultar_historico
from .schemas import HistoricoRendimientosInput, HistoricoRendimientosResponse


class HistoricoRendimientosService:
    def __init__(self, repository):
        self.repository = repository

    def consultar(self, consulta: HistoricoRendimientosInput) -> HistoricoRendimientosResponse:
        return HistoricoRendimientosResponse(**consultar_historico(
            self.repository, consulta, hoy=fecha_actual_ecuador(),
            definiciones=PRODUCTOS_RENDIMIENTO, calcular_componentes=componentes_rendimientos,
            campo_tipo='producto', campo_valor='rendimiento',
        ))

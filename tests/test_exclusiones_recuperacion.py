from datetime import date

from app.modules.analytic.recuperacion.recuperacion_historico.repositories.mongo_recuperacion_historico_repository import (
    MongoRecuperacionHistoricoRepository,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.repositories.mongo_recaudacion_acumulada_repository import (
    MongoRecaudacionAcumuladaRepository,
)
from app.modules.negocios.recuperacion.resumen_recuperacion.repositories.mongo_resumen_recuperacion_repository import (
    MongoResumenRecuperacionRepository,
)


def test_los_calculos_de_recuperacion_excluyen_castigo_y_condonacion_de_mora() -> None:
    corte = date(2026, 11, 24)
    fecha = "20261124"
    actual = "20261125"
    agencias = ["MATRIZ"]
    filtro = {
        "$expr": {
            "$not": [
                {
                    "$in": [
                        {"$ifNull": ["$TIPO_TRANSACCION", "$TipoTransaccion"]},
                        ["CASTIGO DE PRÉSTAMO", "CONDONACION DE INTERES MORA"],
                    ]
                }
            ]
        }
    }

    historico = MongoRecuperacionHistoricoRepository._construir_pipeline(fecha, fecha)
    evaluacion = MongoRecuperacionHistoricoRepository._construir_pipeline_resumen_negocios(
        fecha, fecha, fecha, actual, agencias
    )
    detalle = MongoRecuperacionHistoricoRepository._construir_pipeline_detalle_resumen(
        fecha_desde=fecha,
        fecha_hasta=fecha,
        fecha_corte=actual,
        fecha_actual=actual,
        agencias=agencias,
        dimension="agencia",
        valor_dimension="MATRIZ",
        asesores=[],
        cargos=[],
        offset=0,
        limite=20,
        incluir_actual=True,
    )
    detalle_actual = next(etapa["$unionWith"]["pipeline"] for etapa in detalle if "$unionWith" in etapa)
    resumen = MongoResumenRecuperacionRepository.construir_pipeline([(corte, corte)], agencias)
    recaudacion = MongoRecaudacionAcumuladaRepository._pipeline_recuperaciones(
        fecha, fecha, ["PRESTAMO-1"]
    )

    for pipeline in (historico, evaluacion, detalle, detalle_actual, resumen):
        assert {"$match": filtro} in pipeline
    assert recaudacion[0]["$match"]["$expr"] == filtro["$expr"]

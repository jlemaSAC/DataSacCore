from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from app.modules.analytic.cartera_de_credito.morosidad_historica.domain import (
    DimensionesMorosidad,
    MorosidadAgrupada,
)
from app.modules.analytic.colocacion.colocacion_historico.repositories.mongo_colocacion_historico_repository import (
    _numero_valido,
    _plazo_dias,
    _rango_edad,
    _rango_numerico,
    _rango_plazo,
    _texto_normalizado,
)


MongoDocument = dict[str, Any]


def _numero(campo: str) -> dict[str, Any]:
    return {
        "$convert": {
            "input": f"${campo}",
            "to": "double",
            "onError": 0,
            "onNull": 0,
        }
    }


class MongoMorosidadHistoricaRepository:
    collection_name = "SituacionCrediticia"

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.collection: Collection[MongoDocument] = mongo_db[self.collection_name]

    def obtener_morosidad_agrupada(
        self,
        cortes: dict[str, tuple[int, int]],
    ) -> list[MorosidadAgrupada]:
        if not cortes:
            return []

        dimensiones = {
            "agencia": _texto_normalizado("Agencia"),
            "condicion": _texto_normalizado("TipoCondicion"),
            "tipo_prestamo": _texto_normalizado("TipoPrestamo"),
            "producto": _texto_normalizado("Producto"),
            "segmento": _texto_normalizado("Segmento"),
            "asesor": _texto_normalizado("NombreAsesor", "CodigoAsesor"),
            "provincia": _texto_normalizado("Provincia"),
            "canton": _texto_normalizado("Canton"),
            "parroquia": _texto_normalizado("Parroquia"),
            "educacion": _texto_normalizado(
                "Educacion", "Educación", "NivelEducacion", "NivelDeEducacion"
            ),
            "edad": _rango_edad(),
            "garantia": _texto_normalizado("TipoDeGarantia", "TipoGarantia", "GarantiaTipo"),
            "monto": _rango_numerico(
                "DeudaInicial",
                (
                    (3000, "Hasta 3.000"),
                    (5000, "Hasta 5.000"),
                    (8000, "Hasta 8.000"),
                    (10000, "Hasta 10.000"),
                    (20000, "Hasta 20.000"),
                    (30000, "Hasta 30.000"),
                    (40000, "Hasta 40.000"),
                    (50000, "Hasta 50.000"),
                    (60000, "Hasta 60.000"),
                    (70000, "Hasta 70.000"),
                    (80000, "Hasta 80.000"),
                    (90000, "Hasta 90.000"),
                    (100000, "Hasta 100.000"),
                ),
                "Mas de 100.000",
            ),
            "tasa": _rango_numerico(
                "TasaNominal",
                ((13, "Hasta 13"), (14, "Hasta 14"), (16, "Hasta 16"),
                 (17, "Hasta 17"), (18, "Hasta 18"), (19, "Hasta 19"),
                 (20, "Hasta 20"), (21, "Hasta 21")),
                "Mas de 22",
            ),
            "tasa_valor": _numero_valido("TasaNominal"),
            "tasa_real": _rango_numerico(
                "TasaAnual",
                ((13, "Hasta 13"), (14, "Hasta 14"), (16, "Hasta 16"),
                 (17, "Hasta 17"), (18, "Hasta 18"), (19, "Hasta 19"),
                 (20, "Hasta 20"), (21, "Hasta 21")),
                "Mas de 22",
            ),
            "tasa_real_valor": _numero_valido("TasaAnual"),
            "plazo": _rango_plazo(),
            "plazo_valor": _plazo_dias(),
        }
        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "fecha_corte": {"$in": list(cortes)},
                    "EstadoPrestamo": {"$ne": "CANCELADO"},
                }
            },
            {
                "$project": {
                    "fecha_corte": 1,
                    **dimensiones,
                    "saldo_capital": _numero("SaldoCapital"),
                    "capital_no_devenga": _numero("CapitalNoDevenga"),
                    "capital_vencido": _numero("CapitalVencido"),
                }
            },
            {
                "$group": {
                    "_id": {
                        "fecha_corte": "$fecha_corte",
                        **{campo: f"${campo}" for campo in dimensiones},
                    },
                    "operaciones": {"$sum": 1},
                    "saldo_capital": {"$sum": "$saldo_capital"},
                    "capital_no_devenga": {"$sum": "$capital_no_devenga"},
                    "capital_vencido": {"$sum": "$capital_vencido"},
                }
            },
        ]

        resultado: list[MorosidadAgrupada] = []
        for row in self.collection.aggregate(
            pipeline,
            hint="fecha_corte_1",
            allowDiskUse=True,
        ):
            identificador = row.get("_id") or {}
            fecha_corte = str(identificador.get("fecha_corte") or "")
            periodo = cortes.get(fecha_corte)
            if periodo is None:
                continue
            anio, mes = periodo
            valores: dict[str, Any] = {}
            for campo in dimensiones:
                valor = identificador.get(campo)
                if campo in {"tasa_valor", "tasa_real_valor"}:
                    valores[campo] = (
                        float(valor)
                        if isinstance(valor, int | float) and valor >= 0
                        else None
                    )
                elif campo == "plazo_valor":
                    valores[campo] = (
                        int(valor)
                        if isinstance(valor, int | float) and valor >= 0
                        else None
                    )
                else:
                    texto = str(valor or "SIN DATOS").strip() or "SIN DATOS"
                    valores[campo] = (
                        texto
                        if campo in {"monto", "tasa", "tasa_real", "plazo"}
                        else texto.upper()
                    )

            saldo_capital = float(row.get("saldo_capital") or 0.0)
            capital_no_devenga = float(row.get("capital_no_devenga") or 0.0)
            capital_vencido = float(row.get("capital_vencido") or 0.0)
            resultado.append(
                MorosidadAgrupada(
                    dimensiones=DimensionesMorosidad(
                        periodo=f"{anio:04d}-{mes:02d}",
                        anio=anio,
                        mes=mes,
                        **valores,
                    ),
                    operaciones=int(row.get("operaciones") or 0),
                    saldo_capital=saldo_capital,
                    capital_vigente=saldo_capital - capital_no_devenga - capital_vencido,
                    capital_no_devenga=capital_no_devenga,
                    capital_vencido=capital_vencido,
                )
            )
        return resultado

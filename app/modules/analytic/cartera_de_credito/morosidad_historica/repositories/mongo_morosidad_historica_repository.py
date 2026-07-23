from time import perf_counter
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from app.modules.analytic.cartera_de_credito.morosidad_historica.domain import (
    CorteActualMorosidad,
    DimensionesMorosidad,
    MorosidadAgrupada,
)
from app.modules.analytic.colocacion.colocacion_historico.repositories.mongo_colocacion_historico_repository import (
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


def _numero_opcional(campo: str) -> dict[str, Any]:
    return {
        "$convert": {
            "input": f"${campo}",
            "to": "double",
            "onError": None,
            "onNull": None,
        }
    }


def _cuota_aproximada() -> dict[str, Any]:
    capital = _numero_opcional("DeudaInicial")
    tasa_anual = _numero_opcional("TasaNominal")
    plazo_meses = _numero_opcional("Plazo")
    tasa_mensual = {"$divide": [tasa_anual, 1200]}
    return {
        "$cond": [
            {
                "$and": [
                    {"$ne": [capital, None]},
                    {"$gte": [capital, 0]},
                    {"$ne": [tasa_anual, None]},
                    {"$gte": [tasa_anual, 0]},
                    {"$ne": [plazo_meses, None]},
                    {"$gt": [plazo_meses, 0]},
                ]
            },
            {
                "$cond": [
                    {"$eq": [tasa_anual, 0]},
                    {"$divide": [capital, plazo_meses]},
                    {
                        "$divide": [
                            {"$multiply": [capital, tasa_mensual]},
                            {
                                "$subtract": [
                                    1,
                                    {
                                        "$pow": [
                                            {"$add": [1, tasa_mensual]},
                                            {"$multiply": [-1, plazo_meses]},
                                        ]
                                    },
                                ]
                            },
                        ]
                    },
                ]
            },
            None,
        ]
    }


def _rango_cuota_aproximada() -> dict[str, Any]:
    cuota = _cuota_aproximada()
    rangos = (
        (100, "Hasta 100"),
        (300, "Hasta 300"),
        (500, "Hasta 500"),
        (700, "Hasta 700"),
        (900, "Hasta 900"),
        (1100, "Hasta 1.100"),
        (1300, "Hasta 1.300"),
        (1500, "Hasta 1.500"),
        (1700, "Hasta 1.700"),
        (1900, "Hasta 1.900"),
    )
    return {
        "$switch": {
            "branches": [
                {
                    "case": {
                        "$and": [
                            {"$ne": [cuota, None]},
                            {"$gte": [cuota, 0]},
                            {"$lte": [cuota, limite]},
                        ]
                    },
                    "then": etiqueta,
                }
                for limite, etiqueta in rangos
            ]
            + [
                {
                    "case": {"$gt": [cuota, 1900]},
                    "then": "Mas de 1.900",
                }
            ],
            "default": "SIN DATOS",
        }
    }


def _rango_plazo_meses() -> dict[str, Any]:
    return _rango_numerico(
        "Plazo",
        (
            (12, "Hasta 1 AÑO"),
            (24, "Hasta 2 AÑOS"),
            (36, "Hasta 3 AÑOS"),
            (48, "Hasta 4 AÑOS"),
            (60, "Hasta 5 AÑOS"),
            (72, "Hasta 6 AÑOS"),
            (84, "Hasta 7 AÑOS"),
            (96, "Hasta 8 AÑOS"),
            (120, "Hasta 10 AÑOS"),
        ),
        "Mas de 10 AÑOS",
    )


class MongoMorosidadHistoricaRepository:
    collection_name = "SituacionCrediticia"
    actual_collection_name = "SituacionCrediticiaActual"

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.collection: Collection[MongoDocument] = mongo_db[self.collection_name]
        self.actual_collection: Collection[MongoDocument] = mongo_db[
            self.actual_collection_name
        ]

    def obtener_morosidad_agrupada(
        self,
        cortes: dict[str, tuple[int, int]],
        corte_actual: CorteActualMorosidad | None = None,
    ) -> list[MorosidadAgrupada]:
        if not cortes and corte_actual is None:
            return []

        inicio_total = perf_counter()

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
            "tasa_real": _rango_numerico(
                "TasaAnual",
                ((13, "Hasta 13"), (14, "Hasta 14"), (16, "Hasta 16"),
                 (17, "Hasta 17"), (18, "Hasta 18"), (19, "Hasta 19"),
                 (20, "Hasta 20"), (21, "Hasta 21")),
                "Mas de 22",
            ),
            "plazo": _rango_plazo(),
            "cuota": _rango_cuota_aproximada(),
        }
        dimensiones_actual = {
            **dimensiones,
            "plazo": _rango_plazo_meses(),
        }
        resultado: list[MorosidadAgrupada] = []
        consultas: list[
            tuple[
                str,
                Collection[MongoDocument],
                list[dict[str, Any]],
                dict[str, tuple[int, int]],
                dict[str, Any],
            ]
        ] = []
        if cortes:
            consultas.append(
                (
                    "historico",
                    self.collection,
                    self._construir_pipeline(
                        dimensiones,
                        {
                            "fecha_corte": {"$in": list(cortes)},
                            "EstadoPrestamo": {"$ne": "CANCELADO"},
                        },
                        1,
                    ),
                    cortes,
                    {
                        "hint": "fecha_corte_1_estado_prestamo_1",
                        "allowDiskUse": True,
                    },
                )
            )
        if corte_actual is not None:
            consultas.append(
                (
                    "actual",
                    self.actual_collection,
                    self._construir_pipeline(
                        dimensiones_actual,
                        {"EstadoPrestamo": {"$ne": "CANCELADO"}},
                        {"$literal": corte_actual.fecha_corte},
                    ),
                    {
                        corte_actual.fecha_corte: (
                            corte_actual.anio,
                            corte_actual.mes,
                        )
                    },
                    {"allowDiskUse": True},
                )
            )

        for fuente, collection, pipeline, periodos, opciones in consultas:
            inicio_cursor = perf_counter()
            rows = collection.aggregate(pipeline, **opciones)
            cursor_ms = (perf_counter() - inicio_cursor) * 1000
            inicio_consumo = perf_counter()
            filas_iniciales = len(resultado)
            self._agregar_resultados(resultado, rows, periodos, dimensiones)
            consumo_mapeo_ms = (perf_counter() - inicio_consumo) * 1000
            print(
                "[morosidad-historica][mongo] "
                f"fuente={fuente} cortes={len(periodos)} "
                f"agrupaciones={len(resultado) - filas_iniciales} "
                f"cursor_ms={cursor_ms:.2f} "
                f"consumo_mapeo_ms={consumo_mapeo_ms:.2f}"
            )

        total_ms = (perf_counter() - inicio_total) * 1000
        print(
            "[morosidad-historica][mongo] "
            f"fuentes={len(consultas)} cortes={len(cortes) + int(corte_actual is not None)} "
            f"agrupaciones={len(resultado)} "
            f"total_ms={total_ms:.2f}"
        )
        return resultado

    @staticmethod
    def _construir_pipeline(
        dimensiones: dict[str, Any],
        match: dict[str, Any],
        fecha_corte: int | dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            {"$match": match},
            {
                "$project": {
                    "fecha_corte": fecha_corte,
                    **dimensiones,
                    "saldo_capital": _numero("SaldoCapital"),
                    "cartera_improductiva": {
                        "$add": [
                            _numero("CapitalNoDevenga"),
                            _numero("CapitalVencido"),
                        ]
                    },
                    "provision_requerida": _numero("ProvisionRequerida"),
                }
            },
            {
                "$group": {
                    "_id": {
                        "fecha_corte": "$fecha_corte",
                        **{campo: f"${campo}" for campo in dimensiones},
                    },
                    "saldo_capital": {"$sum": "$saldo_capital"},
                    "cartera_improductiva": {"$sum": "$cartera_improductiva"},
                    "provision_requerida": {"$sum": "$provision_requerida"},
                }
            },
        ]

    @staticmethod
    def _agregar_resultados(
        resultado: list[MorosidadAgrupada],
        rows: Any,
        periodos: dict[str, tuple[int, int]],
        dimensiones: dict[str, Any],
    ) -> None:
        for row in rows:
            identificador = row.get("_id") or {}
            fecha_corte = str(identificador.get("fecha_corte") or "")
            periodo = periodos.get(fecha_corte)
            if periodo is None:
                continue
            anio, mes = periodo
            valores: dict[str, Any] = {}
            for campo in dimensiones:
                valor = identificador.get(campo)
                texto = str(valor or "SIN DATOS").strip() or "SIN DATOS"
                valores[campo] = (
                    texto
                    if campo in {"monto", "tasa", "tasa_real", "plazo", "cuota"}
                    else texto.upper()
                )
            resultado.append(
                MorosidadAgrupada(
                    dimensiones=DimensionesMorosidad(
                        periodo=f"{anio:04d}-{mes:02d}",
                        anio=anio,
                        mes=mes,
                        **valores,
                    ),
                    saldo_capital=float(row.get("saldo_capital") or 0.0),
                    cartera_improductiva=float(row.get("cartera_improductiva") or 0.0),
                    provision_requerida=float(row.get("provision_requerida") or 0.0),
                )
            )

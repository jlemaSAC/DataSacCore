from __future__ import annotations

from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database


MongoDocument = dict[str, Any]


class MongoMatrizTransicionRepository:
    """Obtiene el cierre histórico y el universo operativo de cartera."""

    historico_collection_name = "SituacionCrediticia"
    actual_collection_name = "SituacionCrediticiaActual"

    projection = {
        "_id": 0,
        "IdPrestamo": 1,
        "IDPRESTAMO": 1,
        "id_prestamo": 1,
        "NumeroPrestamo": 1,
        "Calificacion": 1,
        "EstadoPrestamo": 1,
        "CodigoEstadoPrestamo": 1,
        "CodigoEstado": 1,
        "Agencia": 1,
        "IdAgencia": 1,
        "id_agencia": 1,
        "CodigoAsesor": 1,
        "CodigoUsuario": 1,
        "CODIGOUSUARIO": 1,
        "NombreAsesor": 1,
        "NombreCompleto": 1,
        "CargoAsesor": 1,
        "ESDIFERIDO": 1,
        "EsDiferido": 1,
        "Diferido": 1,
        "EsCancelado": 1,
        "SaldoCapital": 1,
        "ProvisionRequerida": 1,
        "ProvisionConstituida": 1,
        "ProvisionConsituida": 1,
        "ExigibleCapital": 1,
        "ExigibleInteres": 1,
        "ExigibleMora": 1,
        "ExigibleOtros": 1,
        "ValorParaEstarAlDia": 1,
        "ValorHastaCuotaActual": 1,
        "ValorCancelarTotal": 1,
        "as_of": 1,
        "updated_at": 1,
        "data_version": 1,
    }

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.historico: Collection[MongoDocument] = mongo_db[self.historico_collection_name]
        self.actual: Collection[MongoDocument] = mongo_db[self.actual_collection_name]

    def obtener_actual_filtrado(
        self,
        *,
        agencias: list[str],
        diferido: bool | None,
        cargos: list[str],
        estados: list[str],
        asesores: list[str],
    ) -> list[MongoDocument]:
        """Lee el estado operativo, aplicando los filtros del corte nuevo en Mongo."""
        filtro = self._construir_filtro_nuevo(
            agencias=agencias,
            diferido=diferido,
            cargos=cargos,
            estados=estados,
            asesores=asesores,
            es_actual=True,
        )
        return list(self.actual.find(filtro, projection=self.projection))

    def obtener_historico_filtrado(
        self,
        fecha_corte: str,
        *,
        agencias: list[str],
        diferido: bool | None,
        cargos: list[str],
        estados: list[str],
        asesores: list[str],
    ) -> list[MongoDocument]:
        """Lee un corte histórico final, filtrándolo antes de enviarlo al servicio."""
        filtro = self._construir_filtro_nuevo(
            agencias=agencias,
            diferido=diferido,
            cargos=cargos,
            estados=estados,
            asesores=asesores,
            es_actual=False,
        )
        filtro["fecha_corte"] = fecha_corte
        cursor = self.historico.find(filtro, projection=self.projection).hint("fecha_corte_1")
        return list(cursor)

    def obtener_anterior_por_prestamos(
        self,
        fecha_corte: str,
        numeros_prestamo: list[str],
        *,
        chunk_size: int = 5_000,
    ) -> list[MongoDocument]:
        """Recupera únicamente el universo previo necesario para las transiciones."""
        if not numeros_prestamo:
            return []

        documentos: list[MongoDocument] = []
        for inicio in range(0, len(numeros_prestamo), chunk_size):
            numeros = numeros_prestamo[inicio : inicio + chunk_size]
            cursor = self.historico.find(
                {
                    "fecha_corte": fecha_corte,
                    "NumeroPrestamo": {"$in": numeros},
                },
                projection=self.projection,
            ).hint("idx_situacion_fecha_prestamo")
            documentos.extend(cursor)
        return documentos

    @staticmethod
    def _construir_filtro_nuevo(
        *,
        agencias: list[str],
        diferido: bool | None,
        cargos: list[str],
        estados: list[str],
        asesores: list[str],
        es_actual: bool,
    ) -> MongoDocument:
        condiciones: list[MongoDocument] = []
        if agencias:
            condiciones.append({"Agencia": {"$in": agencias}})
        if diferido is not None:
            if es_actual:
                condiciones.append({"EsDiferido": diferido})
            else:
                valores = [True, 1, "1", "SI", "SÍ", "S", "TRUE"]
                condiciones.append(
                    {"ESDIFERIDO": {"$in" if diferido else "$nin": valores}}
                )
        if cargos:
            condiciones.append({"CargoAsesor": {"$in": cargos}})
        if estados:
            condiciones.append(
                {
                    "$or": [
                        {"EstadoPrestamo": {"$in": estados}},
                        {"CodigoEstadoPrestamo": {"$in": estados}},
                        {"CodigoEstado": {"$in": estados}},
                    ]
                }
            )
        if asesores:
            condiciones.append(
                {
                    "$or": [
                        {"CodigoAsesor": {"$in": asesores}},
                        {"CodigoUsuario": {"$in": asesores}},
                        {"CODIGOUSUARIO": {"$in": asesores}},
                        {"NombreAsesor": {"$in": asesores}},
                        {"NombreCompleto": {"$in": asesores}},
                    ]
                }
            )
        if not condiciones:
            return {}
        return {"$and": condiciones}

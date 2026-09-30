from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from app.modules.negocios.cartera_de_credito.matriz_transicion.schemas import (
    MatrizTransicionRequest,
    MatrizTransicionResponse,
)


Metricas = dict[str, tuple[str, str]]
METRICAS: Metricas = {
    "saldos_capital": ("SaldoCapital", "saldos_capital"),
    "provision_requerida": ("ProvisionRequerida", "provision_requerida"),
    "provision_constituida": ("ProvisionConstituida", "provision_constituida"),
    "exigible_capital": ("ExigibleCapital", "exigible_capital"),
    "exigible_interes": ("ExigibleInteres", "exigible_interes"),
    "exigible_mora": ("ExigibleMora", "exigible_mora"),
    "exigible_otros": ("ExigibleOtros", "exigible_otros"),
    "valor_para_estar_al_dia": ("ValorParaEstarAlDia", "valor_para_estar_al_dia"),
    "valor_hasta_cuota_actual": ("ValorHastaCuotaActual", "valor_hasta_cuota_actual"),
    "valor_cancelar_total": ("ValorCancelarTotal", "valor_cancelar_total"),
}


def _fecha_corte(value: date) -> str:
    return value.strftime("%Y%m%d")


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip().replace("$", "").replace("%", "")
        if "," in normalized and "." not in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
        try:
            return float(normalized)
        except ValueError:
            return 0.0
    return 0.0


def _normalizar(value: Any) -> str:
    return str(value).strip().upper() if value is not None else ""


def _a_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return _normalizar(value) in {"1", "TRUE", "T", "SI", "SÍ", "S", "YES", "Y"}


class MatrizTransicionService:
    def __init__(self, mongo_repository: Any) -> None:
        self.mongo_repository = mongo_repository

    def obtener(
        self,
        request: MatrizTransicionRequest,
        *,
        hoy: date | None = None,
    ) -> MatrizTransicionResponse:
        fecha_anterior = request.fecha_corte_anterior.date()
        fecha_fin = request.fecha_corte_nuevo.date()

        hoy = hoy or datetime.now().date()
        fecha_anterior_str = _fecha_corte(fecha_anterior)
        fecha_fin_str = _fecha_corte(fecha_fin)
        filtros_nuevo = self._filtros_nuevo(request)

        if fecha_fin == hoy:
            nuevo = self.mongo_repository.obtener_actual_filtrado(**filtros_nuevo)
            fuente_nuevo = "SituacionCrediticiaActual"
        else:
            nuevo = self.mongo_repository.obtener_historico_filtrado(
                fecha_fin_str,
                **filtros_nuevo,
            )
            fuente_nuevo = "SituacionCrediticia"
        numeros_prestamo = sorted(
            {
                str(document.get("NumeroPrestamo") or "").strip()
                for document in nuevo
                if str(document.get("NumeroPrestamo") or "").strip()
            }
        )
        anterior = self.mongo_repository.obtener_anterior_por_prestamos(
            fecha_anterior_str,
            numeros_prestamo,
        )

        return self._construir_matriz(
            anterior=anterior,
            nuevo=nuevo,
            request=request,
            fecha_anterior=fecha_anterior_str,
            fecha_nuevo=fecha_fin_str,
            fuente_nuevo=fuente_nuevo,
        )

    @staticmethod
    def _filtros_nuevo(request: MatrizTransicionRequest) -> dict[str, Any]:
        def valores(value: str | list[str] | None) -> list[str]:
            if value is None:
                return []
            items = value if isinstance(value, list) else [value]
            return [str(item).strip() for item in items if str(item).strip()]

        return {
            "agencias": valores(request.agencia),
            "diferido": request.diferido,
            "cargos": valores(request.cargo),
            "estados": valores(request.estado_prestamo),
            "asesores": valores(request.asesores),
        }

    def _construir_matriz(
        self,
        *,
        anterior: list[dict[str, Any]],
        nuevo: list[dict[str, Any]],
        request: MatrizTransicionRequest,
        fecha_anterior: str,
        fecha_nuevo: str,
        fuente_nuevo: str,
    ) -> MatrizTransicionResponse:
        anterior_por_prestamo = self._indexar(
            anterior,
            lado="anterior",
            request=request,
        )
        nuevo_por_prestamo = self._indexar(
            nuevo,
            lado="nuevo",
            request=request,
        )

        comunes = set(anterior_por_prestamo) & set(nuevo_por_prestamo)
        solo_nuevo = set(nuevo_por_prestamo) - set(anterior_por_prestamo)
        if not comunes and not solo_nuevo:
            raise HTTPException(
                status_code=422,
                detail="No hay préstamos pareados con calificación ni préstamos nuevos según los filtros.",
            )

        categorias = self._categorias(anterior_por_prestamo, nuevo_por_prestamo, comunes, solo_nuevo)
        conteos = self._matriz_inicial(categorias, 0)
        metricas_nuevas = {nombre: self._matriz_inicial(categorias, 0.0) for nombre in METRICAS}
        metricas_variacion = {nombre: self._matriz_inicial(categorias, 0.0) for nombre in METRICAS}
        for numero in comunes:
            previo = anterior_por_prestamo[numero]
            actual = nuevo_por_prestamo[numero]
            antes = previo["calificacion"]
            despues = actual["calificacion"]
            self._acumular(
                antes=antes,
                despues=despues,
                anterior=previo["documento"],
                nuevo=actual["documento"],
                conteos=conteos,
                metricas_nuevas=metricas_nuevas,
                metricas_variacion=metricas_variacion,
            )

        for numero in solo_nuevo:
            actual = nuevo_por_prestamo[numero]
            self._acumular(
                antes="NA",
                despues=actual["calificacion"],
                anterior=None,
                nuevo=actual["documento"],
                conteos=conteos,
                metricas_nuevas=metricas_nuevas,
                metricas_variacion=metricas_variacion,
            )

        probabilidades = {
            antes: {
                despues: round(conteos[antes][despues] / sum(conteos[antes].values()), 6)
                if sum(conteos[antes].values())
                else 0.0
                for despues in categorias
            }
            for antes in categorias
        }
        return MatrizTransicionResponse(
            categorias=categorias,
            conteos=conteos,
            probabilidades=probabilidades,
            **{
                nombre: {
                    f"{alias}_variacion": self._redondear_matriz(metricas_variacion[nombre]),
                    alias: self._redondear_matriz(metricas_nuevas[nombre]),
                }
                for nombre, (_, alias) in METRICAS.items()
            },
            fecha_corte_anterior=fecha_anterior,
            fecha_corte_nuevo=fecha_nuevo,
            fuente_corte_nuevo=fuente_nuevo,
        )

    def _indexar(
        self,
        documents: list[dict[str, Any]],
        *,
        lado: str,
        request: MatrizTransicionRequest,
    ) -> dict[str, dict[str, Any]]:
        resultado: dict[str, dict[str, Any]] = {}
        for document in documents:
            numero = str(document.get("NumeroPrestamo") or "").strip()
            calificacion_documento = str(document.get("Calificacion") or "").strip()
            if not numero or not calificacion_documento:
                continue
            if not self._coincide(document, lado, request):
                continue
            resultado[numero] = {
                "calificacion": calificacion_documento,
                "documento": document,
            }
        return resultado

    def _coincide(
        self,
        document: dict[str, Any],
        lado: str,
        request: MatrizTransicionRequest,
    ) -> bool:
        if lado == "anterior" and self._es_cancelado(document):
            return False
        if lado == "anterior":
            return True

        if request.diferido is not None:
            valor_diferido = document.get("EsDiferido", document.get("ESDIFERIDO", document.get("Diferido")))
            if _a_bool(valor_diferido) is not request.diferido:
                return False

        return all(
            (
                self._coincide_filtro(document, "Agencia", request.agencia),
                self._coincide_filtro(document, "CargoAsesor", request.cargo),
                self._coincide_filtro(document, "EstadoPrestamo", request.estado_prestamo),
                self._coincide_filtro(document, "Asesores", request.asesores),
            )
        )

    def _coincide_filtro(self, document: dict[str, Any], campo: str, esperado: Any) -> bool:
        if esperado is None:
            return True
        valores_esperados = self._valores_esperados(esperado)
        return not valores_esperados or bool(self._valores_documento(document, campo) & valores_esperados)

    def _es_cancelado(self, document: dict[str, Any]) -> bool:
        estados = self._valores_documento(document, "EstadoPrestamo")
        return "CANCELADO" in estados or "C" in estados or _a_bool(document.get("EsCancelado"))

    @staticmethod
    def _valores_esperados(value: Any) -> set[str]:
        items = value if isinstance(value, (list, tuple, set)) else [value]
        valores: set[str] = set()
        for item in items:
            if isinstance(item, dict):
                item_values = item.values()
            else:
                item_values = [item]
            for item_value in item_values:
                normalizado = _normalizar(item_value)
                if normalizado:
                    valores.add(normalizado)
        return valores

    @staticmethod
    def _valores_documento(document: dict[str, Any], campo: str) -> set[str]:
        aliases = {
            "NombreCompleto": ("NombreCompleto", "NombreAsesor"),
            "NombreAsesor": ("NombreAsesor", "NombreCompleto"),
            "CodigoAsesor": ("CodigoAsesor", "CodigoUsuario", "CODIGOUSUARIO"),
            "EstadoPrestamo": ("EstadoPrestamo", "CodigoEstadoPrestamo", "CodigoEstado"),
            "CodigoEstadoPrestamo": ("CodigoEstadoPrestamo", "CodigoEstado", "EstadoPrestamo"),
            "Agencia": ("Agencia", "IdAgencia", "id_agencia"),
            "IdAgencia": ("IdAgencia", "id_agencia", "Agencia"),
            "CargoAsesor": ("CargoAsesor",),
            "Asesores": ("CodigoAsesor", "CodigoUsuario", "CODIGOUSUARIO", "NombreAsesor", "NombreCompleto"),
        }
        return {
            _normalizar(document.get(alias))
            for alias in aliases.get(campo, (campo,))
            if _normalizar(document.get(alias))
        }

    @staticmethod
    def _categorias(
        anterior: dict[str, dict[str, Any]],
        nuevo: dict[str, dict[str, Any]],
        comunes: set[str],
        solo_nuevo: set[str],
    ) -> list[str]:
        categorias = {
            anterior[numero]["calificacion"] for numero in comunes
        } | {
            nuevo[numero]["calificacion"] for numero in comunes | solo_nuevo
        }
        if solo_nuevo:
            categorias.add("NA")
        return sorted(categorias)

    @staticmethod
    def _matriz_inicial(categorias: list[str], valor: int | float) -> dict[str, dict[str, Any]]:
        return {antes: {despues: valor for despues in categorias} for antes in categorias}

    def _acumular(
        self,
        *,
        antes: str,
        despues: str,
        anterior: dict[str, Any] | None,
        nuevo: dict[str, Any],
        conteos: dict[str, dict[str, int]],
        metricas_nuevas: dict[str, dict[str, dict[str, float]]],
        metricas_variacion: dict[str, dict[str, dict[str, float]]],
    ) -> None:
        conteos[antes][despues] += 1
        for nombre, (campo, _) in METRICAS.items():
            metricas_nuevas[nombre][antes][despues] += self._valor_metrica(nuevo, campo)

        for nombre, (campo, _) in METRICAS.items():
            metricas_variacion[nombre][antes][despues] += self._valor_metrica(
                nuevo, campo
            ) - self._valor_metrica(anterior, campo)

    @staticmethod
    def _valor_metrica(document: dict[str, Any] | None, campo: str) -> float:
        if not document:
            return 0.0
        if campo == "ProvisionConstituida":
            return _to_float(
                document.get("ProvisionConstituida", document.get("ProvisionConsituida"))
            )
        return _to_float(document.get(campo))

    @staticmethod
    def _redondear_matriz(matriz: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
        return {
            antes: {despues: round(valor, 2) for despues, valor in fila.items()}
            for antes, fila in matriz.items()
        }

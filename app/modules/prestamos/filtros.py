import hashlib
import json
from datetime import date, datetime
from typing import Any, Mapping

from app.modules.prestamos.normalizadores import (
    normalizar_calificacion,
    normalizar_codigo_usuario,
    normalizar_estado_prestamo,
    normalizar_numero_prestamo,
    normalizar_texto,
    to_int_safe,
)
from app.modules.prestamos.schemas import PrestamoUniverseRequest


FieldCondition = dict[str, Any]


def _unique_normalized(values: list[Any], normalizer) -> list[Any]:
    normalized_values = []
    seen = set()
    for value in values or []:
        normalized = normalizer(value)
        if normalized in (None, "") or normalized in seen:
            continue
        normalized_values.append(normalized)
        seen.add(normalized)
    return normalized_values


def _unique_ints(values: list[Any]) -> list[int]:
    normalized_values = []
    seen = set()
    for value in values or []:
        normalized = to_int_safe(value, default=None)
        if normalized is None or normalized in seen:
            continue
        normalized_values.append(normalized)
        seen.add(normalized)
    return normalized_values


def normalizar_universe_request(request: PrestamoUniverseRequest | Mapping[str, Any]) -> PrestamoUniverseRequest:
    if isinstance(request, PrestamoUniverseRequest):
        payload = request.model_dump()
    else:
        payload = PrestamoUniverseRequest().model_dump()
        payload.update(dict(request))

    payload["ids_prestamo"] = _unique_ints(payload["ids_prestamo"])
    payload["numeros_prestamo"] = _unique_normalized(payload["numeros_prestamo"], normalizar_numero_prestamo)
    payload["agencias"] = _unique_ints(payload["agencias"])
    payload["agencia_nombres"] = _unique_normalized(payload["agencia_nombres"], normalizar_texto)
    payload["codigos_asesor"] = _unique_normalized(payload["codigos_asesor"], normalizar_codigo_usuario)
    payload["codigos_usuario_control"] = _unique_normalized(
        payload["codigos_usuario_control"],
        normalizar_codigo_usuario,
    )
    payload["codigos_usuario_cobranza_apoyo"] = _unique_normalized(
        payload["codigos_usuario_cobranza_apoyo"],
        normalizar_codigo_usuario,
    )
    payload["ids_cargo_asesor"] = _unique_ints(payload["ids_cargo_asesor"])
    payload["estados_prestamo"] = _unique_normalized(payload["estados_prestamo"], normalizar_estado_prestamo)
    payload["calificaciones"] = _unique_normalized(payload["calificaciones"], normalizar_calificacion)
    payload["productos"] = _unique_normalized(payload["productos"], normalizar_texto)
    payload["tipos_prestamo"] = _unique_normalized(payload["tipos_prestamo"], normalizar_texto)
    payload["provincias"] = _unique_normalized(payload["provincias"], normalizar_texto)

    return PrestamoUniverseRequest(**payload)


def _fecha_corte_mongo(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y%m%d")


def _add_in(match: FieldCondition, field: str, values: list[Any]) -> None:
    if values:
        match[field] = {"$in": values}


def _alias_in(fields: list[str], values: list[Any]) -> FieldCondition | None:
    if not values:
        return None
    return {"$or": [{field: {"$in": values}} for field in fields]}


def _add_alias_condition(and_conditions: list[FieldCondition], fields: list[str], values: list[Any]) -> None:
    condition = _alias_in(fields, values)
    if condition:
        and_conditions.append(condition)


def _build_match(filtros: PrestamoUniverseRequest, *, historico: bool) -> FieldCondition:
    match: FieldCondition = {}
    and_conditions: list[FieldCondition] = []

    if historico:
        fecha_corte = _fecha_corte_mongo(filtros.fecha_corte_anterior)
        if fecha_corte:
            match["fecha_corte"] = fecha_corte

    _add_in(match, "IdPrestamo", filtros.ids_prestamo)
    _add_in(match, "NumeroPrestamo", filtros.numeros_prestamo)
    _add_in(match, "IdAgencia", filtros.agencias)
    _add_in(match, "Agencia", filtros.agencia_nombres)
    _add_in(match, "IdCargoAsesor", filtros.ids_cargo_asesor)
    _add_in(match, "Calificacion", filtros.calificaciones)
    _add_in(match, "Producto", filtros.productos)
    _add_in(match, "TipoPrestamo", filtros.tipos_prestamo)
    _add_in(match, "Provincia", filtros.provincias)

    _add_alias_condition(and_conditions, ["CodigoAsesor", "CodigoUsuario"], filtros.codigos_asesor)
    _add_alias_condition(
        and_conditions,
        ["CodigoUsuarioControl", "CodigoUsuarioResponsableControl"],
        filtros.codigos_usuario_control,
    )
    _add_alias_condition(
        and_conditions,
        ["CodigoUsuarioCobranzaApoyo", "CodigoCobranzaApoyo"],
        filtros.codigos_usuario_cobranza_apoyo,
    )

    if filtros.estados_prestamo:
        and_conditions.append(
            {
                "$or": [
                    {"EstadoPrestamo": {"$in": filtros.estados_prestamo}},
                    {"CodigoEstadoPrestamo": {"$in": filtros.estados_prestamo}},
                    {"CodigoEstado": {"$in": filtros.estados_prestamo}},
                ]
            }
        )
    elif filtros.excluir_cancelados:
        and_conditions.append(
            {
                "$and": [
                    {"EstadoPrestamo": {"$nin": ["CANCELADO", "C"]}},
                    {"CodigoEstadoPrestamo": {"$ne": "C"}},
                    {"CodigoEstado": {"$ne": "C"}},
                ]
            }
        )

    if filtros.filtrar_diferidos is not None:
        and_conditions.append(
            {
                "$or": [
                    {"EsDiferido": filtros.filtrar_diferidos},
                    {"ESDIFERIDO": filtros.filtrar_diferidos},
                    {"Diferido": filtros.filtrar_diferidos},
                ]
            }
        )

    if and_conditions:
        match["$and"] = and_conditions

    return match


def build_mongo_match_actual(filtros: PrestamoUniverseRequest | Mapping[str, Any]) -> FieldCondition:
    return _build_match(normalizar_universe_request(filtros), historico=False)


def build_mongo_match_historico(filtros: PrestamoUniverseRequest | Mapping[str, Any]) -> FieldCondition:
    return _build_match(normalizar_universe_request(filtros), historico=True)


def filtros_hash(filtros: PrestamoUniverseRequest | Mapping[str, Any]) -> str:
    filtros_normalizados = normalizar_universe_request(filtros)
    serialized = json.dumps(filtros_normalizados.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

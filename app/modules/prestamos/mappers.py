from datetime import date, datetime
from typing import Any, Mapping

from app.modules.prestamos.constants import FECHA_CORTE_FORMAT
from app.modules.prestamos.metricas import calcular_capital_vigente
from app.modules.prestamos.normalizadores import (
    es_diferido,
    normalizar_calificacion,
    normalizar_codigo_usuario,
    normalizar_estado_prestamo,
    normalizar_numero_prestamo,
    normalizar_texto,
    to_float_safe,
    to_int_safe,
)
from app.modules.prestamos.schemas import PrestamoSnapshot


def format_fecha_corte(value: datetime | date) -> str:
    return value.strftime(FECHA_CORTE_FORMAT)


def pick_first(document: Mapping[str, Any], *field_names: str, default: Any = None) -> Any:
    for field_name in field_names:
        value = document.get(field_name)
        if value is not None and value != "":
            return value
    return default


def prestamo_snapshot_from_mongo(document: Mapping[str, Any]) -> PrestamoSnapshot:
    numero_prestamo = normalizar_numero_prestamo(pick_first(document, "NumeroPrestamo", "numero_prestamo"))
    saldo_capital = to_float_safe(pick_first(document, "SaldoCapital", "saldo_capital"))
    capital_no_devenga = to_float_safe(pick_first(document, "CapitalNoDevenga", "capital_no_devenga"))
    capital_vencido = to_float_safe(pick_first(document, "CapitalVencido", "capital_vencido"))
    capital_vigente = to_float_safe(pick_first(document, "CapitalVigente", "capital_vigente"))

    if capital_vigente == 0.0 and saldo_capital:
        capital_vigente = calcular_capital_vigente(saldo_capital, capital_no_devenga, capital_vencido)

    estado = pick_first(document, "EstadoPrestamo", "estado_prestamo")
    codigo_estado = pick_first(document, "CodigoEstadoPrestamo", "CodigoEstado", "codigo_estado_prestamo")
    provision_data = _calcular_provision_data(document)

    return PrestamoSnapshot(
        id_prestamo=to_int_safe(pick_first(document, "IdPrestamo", "id_prestamo"), default=None),
        numero_prestamo=numero_prestamo,
        id_agencia=to_int_safe(pick_first(document, "IdAgencia", "id_agencia"), default=None),
        agencia=normalizar_texto(pick_first(document, "Agencia", "agencia"), default="") or None,
        codigo_estado_prestamo=normalizar_estado_prestamo(codigo_estado) or None,
        estado_prestamo=normalizar_estado_prestamo(estado) or None,
        es_cancelado=_es_cancelado(codigo_estado, estado),
        es_diferido=es_diferido(pick_first(document, "EsDiferido", "ESDIFERIDO", "Diferido")),
        codigo_asesor=normalizar_codigo_usuario(
            pick_first(document, "CodigoAsesor", "CodigoUsuario", "codigo_asesor")
        )
        or None,
        nombre_asesor=normalizar_texto(
            pick_first(document, "NombreAsesor", "NombreCompleto", "nombre_asesor"),
            default="",
        )
        or None,
        id_cargo_asesor=to_int_safe(pick_first(document, "IdCargoAsesor", "id_cargo_asesor"), default=None),
        cargo_asesor=normalizar_texto(pick_first(document, "CargoAsesor", "cargo_asesor"), default="") or None,
        codigo_usuario_control=normalizar_codigo_usuario(
            pick_first(
                document,
                "CodigoUsuarioControl",
                "CodigoUsuarioResponsableControl",
                "codigo_usuario_control",
            )
        )
        or None,
        usuario_control=normalizar_texto(pick_first(document, "UsuarioControl", "usuario_control"), default="")
        or None,
        codigo_usuario_cobranza_apoyo=normalizar_codigo_usuario(
            pick_first(
                document,
                "CodigoUsuarioCobranzaApoyo",
                "CodigoCobranzaApoyo",
                "codigo_usuario_cobranza_apoyo",
            )
        )
        or None,
        cobranza_apoyo=normalizar_texto(pick_first(document, "CobranzaApoyo", "cobranza_apoyo"), default="")
        or None,
        calificacion=normalizar_calificacion(pick_first(document, "Calificacion", "calificacion")) or None,
        dias_vencidos=to_int_safe(pick_first(document, "DiasVencidos", "dias_vencidos"), default=0) or 0,
        producto=normalizar_texto(pick_first(document, "Producto", "producto"), default="") or None,
        tipo_prestamo=normalizar_texto(pick_first(document, "TipoPrestamo", "tipo_prestamo"), default="") or None,
        provincia=normalizar_texto(pick_first(document, "Provincia", "provincia"), default="") or None,
        saldo_capital=saldo_capital,
        capital_vigente=capital_vigente,
        capital_no_devenga=capital_no_devenga,
        capital_vencido=capital_vencido,
        provision_requerida=provision_data["provision_requerida"],
        provision_requerida_fuente=provision_data["provision_requerida_fuente"],
        provision_requerida_calculada=provision_data["provision_requerida_calculada"],
        provision_constituida=to_float_safe(
            pick_first(
                document,
                "ProvisionConstituida",
                "ProvisionConsituida",
                "provision_constituida",
            )
        ),
        porcentaje_provision_aplicado=provision_data["porcentaje_provision_aplicado"],
        porcentaje_provision_fuente=provision_data["porcentaje_provision_fuente"],
        porcentaje_provision_minimo=provision_data["porcentaje_provision_minimo"],
        porcentaje_provision_maximo=provision_data["porcentaje_provision_maximo"],
        es_porcentaje_fijo=provision_data["es_porcentaje_fijo"],
        provision_diferencia_validacion=provision_data["provision_diferencia_validacion"],
        exigible_capital=to_float_safe(pick_first(document, "ExigibleCapital", "exigible_capital")),
        exigible_interes=to_float_safe(pick_first(document, "ExigibleInteres", "exigible_interes")),
        exigible_mora=to_float_safe(pick_first(document, "ExigibleMora", "exigible_mora")),
        exigible_otros=to_float_safe(pick_first(document, "ExigibleOtros", "exigible_otros")),
        valor_para_estar_al_dia=to_float_safe(
            pick_first(document, "ValorParaEstarAlDia", "valor_para_estar_al_dia")
        ),
        valor_hasta_cuota_actual=to_float_safe(
            pick_first(document, "ValorHastaCuotaActual", "valor_hasta_cuota_actual")
        ),
        valor_cancelar_total=to_float_safe(pick_first(document, "ValorCancelarTotal", "valor_cancelar_total")),
        data_version=pick_first(document, "data_version", "DataVersion"),
    )


def prestamo_snapshot_from_sql_row(row: Mapping[str, Any]) -> PrestamoSnapshot:
    return prestamo_snapshot_from_mongo(row)


def mongo_document_from_snapshot(
    snapshot: PrestamoSnapshot,
    *,
    as_of: datetime,
    data_version: str,
    source: str = "sql_core",
) -> dict[str, Any]:
    return {
        "IdPrestamo": snapshot.id_prestamo,
        "NumeroPrestamo": snapshot.numero_prestamo,
        "IdAgencia": snapshot.id_agencia,
        "Agencia": snapshot.agencia,
        "CodigoEstadoPrestamo": snapshot.codigo_estado_prestamo,
        "EstadoPrestamo": snapshot.estado_prestamo,
        "EsCancelado": snapshot.es_cancelado,
        "EsDiferido": snapshot.es_diferido,
        "CodigoAsesor": snapshot.codigo_asesor,
        "CodigoUsuario": snapshot.codigo_asesor,
        "NombreAsesor": snapshot.nombre_asesor,
        "NombreCompleto": snapshot.nombre_asesor,
        "IdCargoAsesor": snapshot.id_cargo_asesor,
        "CargoAsesor": snapshot.cargo_asesor,
        "CodigoUsuarioControl": snapshot.codigo_usuario_control,
        "UsuarioControl": snapshot.usuario_control,
        "CodigoUsuarioCobranzaApoyo": snapshot.codigo_usuario_cobranza_apoyo,
        "CobranzaApoyo": snapshot.cobranza_apoyo,
        "Calificacion": snapshot.calificacion,
        "DiasVencidos": snapshot.dias_vencidos,
        "Producto": snapshot.producto,
        "TipoPrestamo": snapshot.tipo_prestamo,
        "Provincia": snapshot.provincia,
        "SaldoCapital": snapshot.saldo_capital,
        "CapitalVigente": snapshot.capital_vigente,
        "CapitalNoDevenga": snapshot.capital_no_devenga,
        "CapitalVencido": snapshot.capital_vencido,
        "ProvisionRequerida": snapshot.provision_requerida,
        "ProvisionRequeridaFuente": snapshot.provision_requerida_fuente,
        "ProvisionRequeridaCalculada": snapshot.provision_requerida_calculada,
        "ProvisionConstituida": snapshot.provision_constituida,
        "PorcentajeProvisionAplicado": snapshot.porcentaje_provision_aplicado,
        "PorcentajeProvisionFuente": snapshot.porcentaje_provision_fuente,
        "PorcentajeProvisionMinimo": snapshot.porcentaje_provision_minimo,
        "PorcentajeProvisionMaximo": snapshot.porcentaje_provision_maximo,
        "EsPorcentajeFijo": snapshot.es_porcentaje_fijo,
        "ProvisionDiferenciaValidacion": snapshot.provision_diferencia_validacion,
        "ExigibleCapital": snapshot.exigible_capital,
        "ExigibleInteres": snapshot.exigible_interes,
        "ExigibleMora": snapshot.exigible_mora,
        "ExigibleOtros": snapshot.exigible_otros,
        "ValorParaEstarAlDia": snapshot.valor_para_estar_al_dia,
        "ValorHastaCuotaActual": snapshot.valor_hasta_cuota_actual,
        "ValorCancelarTotal": snapshot.valor_cancelar_total,
        "source": source,
        "as_of": as_of,
        "data_version": data_version,
        "updated_at": as_of,
    }


def _es_cancelado(codigo_estado: Any, estado: Any) -> bool:
    return normalizar_estado_prestamo(codigo_estado) == "C" or normalizar_estado_prestamo(estado) == "CANCELADO"


def _calcular_provision_data(document: Mapping[str, Any]) -> dict[str, float | bool]:
    provision_requerida_existente = to_float_safe(pick_first(document, "ProvisionRequerida", "provision_requerida"))
    provision_fuente = _calcular_provision_fuente(document)
    saldo_base = to_float_safe(
        pick_first(
            document,
            "SaldoBaseProvision",
            "SaldoProvision",
            "SaldoCalificacion",
            "saldo_base_provision",
        )
    )
    porcentaje_fuente = to_float_safe(
        pick_first(
            document,
            "PorcentajeProvisionFuente",
            "PorcentajeProvision",
            "PorcentajeFijo",
            "porcentaje_provision_fuente",
        )
    )
    porcentaje_regla_fijo = to_float_safe(pick_first(document, "PorcentajeProvisionReglaFijo", "PorcentajeFijoRegla"))
    porcentaje_minimo = to_float_safe(pick_first(document, "PorcentajeProvisionMinimo", "PorcentajeMinimo"))
    porcentaje_maximo = to_float_safe(pick_first(document, "PorcentajeProvisionMaximo", "PorcentajeMaximo"))
    es_porcentaje_fijo = es_diferido(pick_first(document, "EsPorcentajeFijo", "es_porcentaje_fijo"))
    porcentaje_aplicado = _calcular_porcentaje_provision_aplicado(
        porcentaje_fuente=porcentaje_fuente,
        porcentaje_regla_fijo=porcentaje_regla_fijo,
        porcentaje_minimo=porcentaje_minimo,
        porcentaje_maximo=porcentaje_maximo,
        es_porcentaje_fijo=es_porcentaje_fijo,
    )
    provision_calculada = max(saldo_base * porcentaje_aplicado / 100, 0.0) if saldo_base > 0 else 0.0
    provision_requerida = provision_calculada if provision_calculada > 0 else provision_requerida_existente

    return {
        "provision_requerida": provision_requerida,
        "provision_requerida_fuente": provision_fuente,
        "provision_requerida_calculada": provision_calculada,
        "porcentaje_provision_aplicado": porcentaje_aplicado,
        "porcentaje_provision_fuente": porcentaje_fuente,
        "porcentaje_provision_minimo": porcentaje_minimo,
        "porcentaje_provision_maximo": porcentaje_maximo,
        "es_porcentaje_fijo": es_porcentaje_fijo,
        "provision_diferencia_validacion": provision_fuente - provision_calculada,
    }


def _calcular_provision_fuente(document: Mapping[str, Any]) -> float:
    provision_fuente = to_float_safe(pick_first(document, "ProvisionRequeridaFuente", "provision_requerida_fuente"))
    if provision_fuente > 0:
        return provision_fuente

    provision_automatica = to_float_safe(pick_first(document, "ProvisionAutomatica", "ProvisionAutomaticaFuente"))
    provision_manual = to_float_safe(pick_first(document, "ProvisionManual", "ProvisionManualFuente"))
    return max(provision_automatica + provision_manual, 0.0)


def _calcular_porcentaje_provision_aplicado(
    *,
    porcentaje_fuente: float,
    porcentaje_regla_fijo: float,
    porcentaje_minimo: float,
    porcentaje_maximo: float,
    es_porcentaje_fijo: bool,
) -> float:
    if es_porcentaje_fijo:
        return porcentaje_regla_fijo if porcentaje_regla_fijo > 0 else porcentaje_fuente

    porcentaje = porcentaje_fuente
    if porcentaje_minimo > 0:
        porcentaje = max(porcentaje, porcentaje_minimo)
    if porcentaje_maximo > 0:
        porcentaje = min(porcentaje, porcentaje_maximo)
    return porcentaje

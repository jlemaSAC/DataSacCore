from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.schemas import (
    SituacionCrediticiaAsesoresResponse,
)


def _validar_rango_mismo_mes(fecha_inicio: date, fecha_fin: date) -> None:
    if fecha_inicio > fecha_fin:
        raise HTTPException(
            status_code=400,
            detail="fecha_inicio no puede ser posterior a fecha_fin",
        )
    if (fecha_inicio.year, fecha_inicio.month) != (fecha_fin.year, fecha_fin.month):
        raise HTTPException(
            status_code=400,
            detail="fecha_inicio y fecha_fin deben pertenecer al mismo mes",
        )


def _fecha_corte(fecha: date) -> str:
    return fecha.strftime("%Y%m%d")


def _fecha_cierre_mes_anterior(fecha: date) -> str:
    primer_dia_mes = date(fecha.year, fecha.month, 1)
    return _fecha_corte(primer_dia_mes - timedelta(days=1))


def _to_float_safe(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").replace("$", ""))
        except ValueError:
            return 0.0
    return 0.0


def _normalizar_agencia(value: Any) -> str | None:
    agencia = str(value or "").strip()
    return agencia or None


def _clave_agencia(value: Any) -> str | None:
    agencia = _normalizar_agencia(value)
    return agencia.casefold() if agencia else None


def _normalizar_numero_prestamo(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


def _codigo_usuario(document: dict[str, Any]) -> str | None:
    value = document.get("CodigoUsuario") or document.get("CodigoAsesor")
    if value is None:
        return None
    codigo = str(value).strip()
    return codigo or None


def _es_diferido(document: dict[str, Any]) -> bool:
    value = document.get("ESDIFERIDO")
    if value is None:
        value = document.get("EsDiferido", document.get("Diferido"))
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in {"SI", "S", "TRUE", "1"}:
            return True
        if normalized in {"NO", "N", "FALSE", "0"}:
            return False
    return bool(value)


def _filtrar_diferidos(
    documents: list[dict[str, Any]],
    filtrar_diferidos: bool | None,
) -> list[dict[str, Any]]:
    if filtrar_diferidos is None:
        return documents
    return [
        document
        for document in documents
        if _es_diferido(document) is filtrar_diferidos
    ]


def _clave_usuario_agencia(
    codigo: str,
    agencia: str | None,
    separar_por_agencia: bool,
) -> str:
    if separar_por_agencia and agencia:
        return f"{codigo}::{agencia}"
    return codigo


def _valores_normalizados(origen: dict[str, Any]) -> dict[str, Any]:
    saldo = _to_float_safe(origen.get("SaldoCapital"))
    capital_no_devenga = _to_float_safe(origen.get("CapitalNoDevenga"))
    capital_vencido = _to_float_safe(origen.get("CapitalVencido"))
    provision = _to_float_safe(origen.get("ProvisionRequerida"))
    cartera_improductiva = capital_no_devenga + capital_vencido
    capital_vigente = _to_float_safe(origen.get("CapitalVigente"))
    if not capital_vigente:
        capital_vigente = saldo - cartera_improductiva
    mora = cartera_improductiva / saldo if saldo else 0.0

    return {
        "Operaciones": int(origen.get("Operaciones", 0) or 0),
        "Clientes": int(origen.get("Clientes", 0) or 0),
        "SaldoCapital": round(saldo, 2),
        "CapitalVigente": round(capital_vigente, 2),
        "CapitalNoDevenga": round(capital_no_devenga, 2),
        "CapitalVencido": round(capital_vencido, 2),
        "ProvisionRequerida": round(provision, 2),
        "CarteraImproductiva": round(cartera_improductiva, 2),
        "Mora": round(mora, 6),
        "MoraPorcentaje": round(mora * 100, 2),
    }


def _provision_requerida(
    document: dict[str, Any],
    *,
    preferir_calculada: bool,
) -> float:
    provision_calculada = _to_float_safe(document.get("ProvisionRequeridaCalculada"))
    if preferir_calculada and provision_calculada > 0:
        return provision_calculada
    return _to_float_safe(document.get("ProvisionRequerida"))


def _agrupar_por_asesor(
    documents: list[dict[str, Any]],
    reasignaciones: dict[str, str],
    separar_por_agencia: bool,
    *,
    preferir_provision_calculada: bool,
) -> dict[str, dict[str, Any]]:
    resultado: dict[str, dict[str, Any]] = {}

    for document in documents:
        numero = _normalizar_numero_prestamo(document.get("NumeroPrestamo"))
        codigo_original = _codigo_usuario(document)
        codigo_usuario = reasignaciones.get(numero, codigo_original) if numero else codigo_original
        if not codigo_usuario:
            continue

        agencia = _normalizar_agencia(document.get("Agencia"))
        clave = _clave_usuario_agencia(codigo_usuario, agencia, separar_por_agencia)
        if clave not in resultado:
            resultado[clave] = {
                "CodigoUsuario": codigo_usuario,
                "CodigoBase": codigo_usuario,
                "CodigoClave": clave,
                "NombreAsesor": document.get("NombreAsesor"),
                "CargoAsesor": document.get("CargoAsesor"),
                "Agencia": agencia,
                "Operaciones": 0,
                "ClientesSet": set(),
                "SaldoCapital": 0.0,
                "CapitalNoDevenga": 0.0,
                "CapitalVencido": 0.0,
                "ProvisionRequerida": 0.0,
            }

        acumulado = resultado[clave]
        if not acumulado.get("CargoAsesor") and document.get("CargoAsesor"):
            acumulado["CargoAsesor"] = document.get("CargoAsesor")

        acumulado["Operaciones"] += 1
        if document.get("Cliente") is not None:
            acumulado["ClientesSet"].add(document.get("Cliente"))
        acumulado["SaldoCapital"] += _to_float_safe(document.get("SaldoCapital"))
        acumulado["CapitalNoDevenga"] += _to_float_safe(document.get("CapitalNoDevenga"))
        acumulado["CapitalVencido"] += _to_float_safe(document.get("CapitalVencido"))
        acumulado["ProvisionRequerida"] += _provision_requerida(
            document,
            preferir_calculada=preferir_provision_calculada,
        )

    for clave, acumulado in list(resultado.items()):
        resultado[clave] = {
            "CodigoUsuario": acumulado["CodigoBase"],
            "CodigoBase": acumulado["CodigoBase"],
            "CodigoClave": clave,
            "NombreAsesor": acumulado.get("NombreAsesor"),
            "CargoAsesor": acumulado.get("CargoAsesor"),
            "Agencia": acumulado.get("Agencia"),
            "Valores": _valores_normalizados(
                {
                    "Operaciones": acumulado["Operaciones"],
                    "Clientes": len(acumulado["ClientesSet"]),
                    "SaldoCapital": acumulado["SaldoCapital"],
                    "CapitalNoDevenga": acumulado["CapitalNoDevenga"],
                    "CapitalVencido": acumulado["CapitalVencido"],
                    "ProvisionRequerida": acumulado["ProvisionRequerida"],
                }
            ),
        }
    return resultado


def _obtener_reasignaciones(
    actuales: list[dict[str, Any]],
    historicos: list[dict[str, Any]],
) -> dict[str, str]:
    actuales_por_prestamo: dict[str, str] = {}
    for document in actuales:
        numero = _normalizar_numero_prestamo(document.get("NumeroPrestamo"))
        codigo = _codigo_usuario(document)
        if numero and codigo:
            actuales_por_prestamo[numero] = codigo

    reasignaciones: dict[str, str] = {}
    for document in historicos:
        numero = _normalizar_numero_prestamo(document.get("NumeroPrestamo"))
        codigo_historico = _codigo_usuario(document)
        codigo_actual = actuales_por_prestamo.get(numero) if numero else None
        if numero and codigo_historico and codigo_actual and codigo_historico != codigo_actual:
            reasignaciones[numero] = codigo_actual
    return reasignaciones


def _diferencia_valores(
    actuales: dict[str, Any] | None,
    historicos: dict[str, Any] | None,
) -> dict[str, Any]:
    actuales = actuales or {}
    historicos = historicos or {}
    diferencias: dict[str, Any] = {}
    campos = (
        "Operaciones",
        "Clientes",
        "SaldoCapital",
        "CapitalVigente",
        "CapitalNoDevenga",
        "CapitalVencido",
        "ProvisionRequerida",
        "CarteraImproductiva",
        "Mora",
        "MoraPorcentaje",
    )
    for campo in campos:
        delta = (actuales.get(campo, 0) or 0) - (historicos.get(campo, 0) or 0)
        diferencias[campo] = int(round(delta)) if campo in {"Operaciones", "Clientes"} else round(delta, 6)
    return diferencias


class SituacionCrediticiaAsesoresService:
    def __init__(self, mongo_repository: Any, sql_repository: Any) -> None:
        self.mongo_repository = mongo_repository
        self.sql_repository = sql_repository

    def obtener(
        self,
        *,
        fecha_inicio: date,
        fecha_fin: date,
        id_agencia: int = 0,
        filtrar_diferidos: bool | None = None,
        ahora: datetime | None = None,
    ) -> SituacionCrediticiaAsesoresResponse:
        _validar_rango_mismo_mes(fecha_inicio, fecha_fin)
        ahora = ahora or datetime.now()
        fecha_corte_actual_disponible = (
            self.mongo_repository.obtener_ultimo_corte_actual()
            or ahora.strftime("%Y%m%d")
        )
        fecha_corte_fin = _fecha_corte(fecha_fin)
        fecha_corte_cierre_mes_anterior = _fecha_cierre_mes_anterior(fecha_inicio)
        separar_por_agencia = id_agencia == 0

        agencia_nombre: str | None = None
        if id_agencia:
            agencia_nombre = self.sql_repository.obtener_nombre_agencia(id_agencia)
            if not agencia_nombre:
                raise HTTPException(status_code=404, detail="La agencia no existe")

        if fecha_corte_fin == fecha_corte_actual_disponible:
            finales_sin_filtro = self.mongo_repository.obtener_actual(
                fecha_corte_fin,
                agencia_nombre,
            )
        else:
            finales_sin_filtro = self.mongo_repository.obtener_historico(
                fecha_corte_fin,
                agencia_nombre,
            )

        cierres_mes_anterior_sin_filtro = self.mongo_repository.obtener_historico(
            fecha_corte_cierre_mes_anterior,
            agencia_nombre,
        )

        reasignaciones_cierre_mes_anterior = _obtener_reasignaciones(
            finales_sin_filtro,
            cierres_mes_anterior_sin_filtro,
        )
        finales = _filtrar_diferidos(finales_sin_filtro, filtrar_diferidos)
        cierres_mes_anterior = _filtrar_diferidos(
            cierres_mes_anterior_sin_filtro,
            filtrar_diferidos,
        )

        finales_por_asesor = _agrupar_por_asesor(
            finales,
            {},
            separar_por_agencia,
            preferir_provision_calculada=fecha_corte_fin != fecha_corte_actual_disponible,
        )
        cierres_mes_anterior_por_asesor = _agrupar_por_asesor(
            cierres_mes_anterior,
            reasignaciones_cierre_mes_anterior,
            separar_por_agencia,
            preferir_provision_calculada=True,
        )

        comparacion: list[dict[str, Any]] = []
        for clave in sorted(
            set(finales_por_asesor)
            | set(cierres_mes_anterior_por_asesor)
        ):
            actual = finales_por_asesor.get(clave)
            cierre_mes_anterior = cierres_mes_anterior_por_asesor.get(clave)
            codigo_base = (
                actual.get("CodigoBase")
                if actual
                else cierre_mes_anterior.get("CodigoBase")
                if cierre_mes_anterior
                else clave
            )
            cargo_actual = actual.get("CargoAsesor") if actual else None
            if not cargo_actual and cierre_mes_anterior:
                cargo_actual = cierre_mes_anterior.get("CargoAsesor")

            comparacion.append(
                {
                    "CodigoUsuario": codigo_base,
                    "NombreAsesorActual": actual.get("NombreAsesor") if actual else None,
                    "NombreAsesorCierreMesAnterior": (
                        cierre_mes_anterior.get("NombreAsesor")
                        if cierre_mes_anterior
                        else None
                    ),
                    "AgenciaActual": actual.get("Agencia") if actual else None,
                    "AgenciaCierreMesAnterior": (
                        cierre_mes_anterior.get("Agencia")
                        if cierre_mes_anterior
                        else None
                    ),
                    "ValoresActual": actual.get("Valores") if actual else None,
                    "ValoresCierreMesAnterior": (
                        cierre_mes_anterior.get("Valores")
                        if cierre_mes_anterior
                        else None
                    ),
                    "DiferenciasCierreMesAnterior": _diferencia_valores(
                        actual.get("Valores") if actual else None,
                        cierre_mes_anterior.get("Valores")
                        if cierre_mes_anterior
                        else None,
                    ),
                    "CargoAsesorActual": cargo_actual,
                }
            )

        comparacion.sort(
            key=lambda item: (
                0 if (item.get("CargoAsesorActual") or "").strip().upper() == "ASESOR DE NEGOCIOS" else 1,
                item.get("CodigoUsuario") or "",
            )
        )

        agencias_respuesta = sorted(
            {
                agencia
                for item in comparacion
                for agencia in (
                    _normalizar_agencia(item.get("AgenciaActual")),
                    _normalizar_agencia(item.get("AgenciaCierreMesAnterior")),
                )
                if agencia
            }
        )
        agencias_gerentes = self.sql_repository.obtener_gerentes_oficina(agencias_respuesta)

        faltantes_en_cierre_mes_anterior = sorted(
            str(finales_por_asesor[key].get("CodigoBase") or key)
            for key in finales_por_asesor.keys() - cierres_mes_anterior_por_asesor.keys()
        )
        faltantes_en_actual = sorted(
            str(cierres_mes_anterior_por_asesor[key].get("CodigoBase") or key)
            for key in cierres_mes_anterior_por_asesor.keys() - finales_por_asesor.keys()
        )

        return SituacionCrediticiaAsesoresResponse(
            fecha_corte_actual=fecha_corte_fin,
            fecha_corte_cierre_mes_anterior=fecha_corte_cierre_mes_anterior,
            comparacion=comparacion,
            agencias_gerentes_oficina=agencias_gerentes,
            faltantes_en_cierre_mes_anterior=faltantes_en_cierre_mes_anterior,
            faltantes_en_actual=faltantes_en_actual,
        )

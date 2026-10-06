from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException

from app.modules.negocios.cartera_de_credito.cartera_improductiva.schemas import (
    CarteraImproductivaResponse,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.service import (
    _agrupar_por_asesor,
    _fecha_corte,
    _filtrar_diferidos,
    _normalizar_agencia,
    _obtener_reasignaciones,
)


def _valores_cartera_improductiva(
    asesor: dict[str, Any] | None,
) -> dict[str, float] | None:
    if asesor is None:
        return None

    valores = asesor["Valores"]
    return {
        "SaldoCapital": valores["SaldoCapital"],
        "CarteraImproductiva": valores["CarteraImproductiva"],
        "Morosidad": valores["Mora"],
        "MorosidadPorcentaje": valores["MoraPorcentaje"],
    }


def _validar_rango(fecha_inicio: date, fecha_fin: date) -> None:
    if fecha_inicio > fecha_fin:
        raise HTTPException(
            status_code=400,
            detail="fecha_inicio no puede ser posterior a fecha_fin",
        )


class CarteraImproductivaService:
    def __init__(self, mongo_repository: Any, sql_repository: Any) -> None:
        self.mongo_repository = mongo_repository
        self.sql_repository = sql_repository

    def _obtener_corte(
        self,
        fecha_corte: str,
        fecha_corte_actual_disponible: str,
        agencia_nombre: str | None,
    ) -> list[dict[str, Any]]:
        if fecha_corte == fecha_corte_actual_disponible:
            return self.mongo_repository.obtener_actual(fecha_corte, agencia_nombre)
        return self.mongo_repository.obtener_historico(fecha_corte, agencia_nombre)

    def obtener(
        self,
        *,
        fecha_inicio: date,
        fecha_fin: date,
        id_agencia: int = 0,
        filtrar_diferidos: bool | None = None,
        ahora: datetime | None = None,
    ) -> CarteraImproductivaResponse:
        _validar_rango(fecha_inicio, fecha_fin)
        ahora = ahora or datetime.now()
        fecha_corte_actual_disponible = (
            self.mongo_repository.obtener_ultimo_corte_actual()
            or ahora.strftime("%Y%m%d")
        )
        fecha_corte_fin = _fecha_corte(fecha_fin)
        fecha_corte_inicio = _fecha_corte(fecha_inicio)
        fecha_corte_dia_anterior_fin = _fecha_corte(
            fecha_fin - timedelta(days=1)
        )
        separar_por_agencia = id_agencia == 0

        agencia_nombre: str | None = None
        if id_agencia:
            agencia_nombre = self.sql_repository.obtener_nombre_agencia(id_agencia)
            if not agencia_nombre:
                raise HTTPException(status_code=404, detail="La agencia no existe")

        documentos_fin_sin_filtro = self._obtener_corte(
            fecha_corte_fin,
            fecha_corte_actual_disponible,
            agencia_nombre,
        )
        documentos_inicio_sin_filtro = self._obtener_corte(
            fecha_corte_inicio,
            fecha_corte_actual_disponible,
            agencia_nombre,
        )
        documentos_dia_anterior_sin_filtro = self._obtener_corte(
            fecha_corte_dia_anterior_fin,
            fecha_corte_actual_disponible,
            agencia_nombre,
        )

        reasignaciones_inicio = _obtener_reasignaciones(
            documentos_fin_sin_filtro,
            documentos_inicio_sin_filtro,
        )
        reasignaciones_dia_anterior = _obtener_reasignaciones(
            documentos_fin_sin_filtro,
            documentos_dia_anterior_sin_filtro,
        )
        documentos_fin = _filtrar_diferidos(
            documentos_fin_sin_filtro,
            filtrar_diferidos,
        )
        documentos_inicio = _filtrar_diferidos(
            documentos_inicio_sin_filtro,
            filtrar_diferidos,
        )
        documentos_dia_anterior = _filtrar_diferidos(
            documentos_dia_anterior_sin_filtro,
            filtrar_diferidos,
        )

        por_asesor_fin = _agrupar_por_asesor(
            documentos_fin,
            {},
            separar_por_agencia,
            preferir_provision_calculada=fecha_corte_fin != fecha_corte_actual_disponible,
        )
        por_asesor_inicio = _agrupar_por_asesor(
            documentos_inicio,
            reasignaciones_inicio,
            separar_por_agencia,
            preferir_provision_calculada=fecha_corte_inicio != fecha_corte_actual_disponible,
        )
        por_asesor_dia_anterior = _agrupar_por_asesor(
            documentos_dia_anterior,
            reasignaciones_dia_anterior,
            separar_por_agencia,
            preferir_provision_calculada=(
                fecha_corte_dia_anterior_fin != fecha_corte_actual_disponible
            ),
        )

        claves = (
            set(por_asesor_fin)
            | set(por_asesor_inicio)
            | set(por_asesor_dia_anterior)
        )
        comparacion: list[dict[str, Any]] = []
        for clave in sorted(claves):
            fin = por_asesor_fin.get(clave)
            inicio = por_asesor_inicio.get(clave)
            dia_anterior = por_asesor_dia_anterior.get(clave)
            asesor_base = fin or inicio or dia_anterior
            if asesor_base is None:
                continue

            comparacion.append(
                {
                    "CodigoUsuario": asesor_base["CodigoBase"],
                    "NombreAsesorFechaFin": fin.get("NombreAsesor") if fin else None,
                    "NombreAsesorFechaInicio": (
                        inicio.get("NombreAsesor") if inicio else None
                    ),
                    "NombreAsesorDiaAnteriorFechaFin": (
                        dia_anterior.get("NombreAsesor") if dia_anterior else None
                    ),
                    "CargoAsesorFechaFin": (
                        fin.get("CargoAsesor")
                        if fin
                        else inicio.get("CargoAsesor")
                        if inicio
                        else dia_anterior.get("CargoAsesor")
                    ),
                    "AgenciaFechaFin": fin.get("Agencia") if fin else None,
                    "AgenciaFechaInicio": inicio.get("Agencia") if inicio else None,
                    "AgenciaDiaAnteriorFechaFin": (
                        dia_anterior.get("Agencia") if dia_anterior else None
                    ),
                    "ValoresFechaFin": _valores_cartera_improductiva(fin),
                    "ValoresFechaInicio": _valores_cartera_improductiva(inicio),
                    "ValoresDiaAnteriorFechaFin": _valores_cartera_improductiva(
                        dia_anterior
                    ),
                }
            )

        comparacion.sort(
            key=lambda item: (
                0
                if (item.get("CargoAsesorFechaFin") or "").strip().upper()
                == "ASESOR DE NEGOCIOS"
                else 1,
                item["CodigoUsuario"],
            )
        )
        agencias = sorted(
            {
                agencia
                for item in comparacion
                for agencia in (
                    _normalizar_agencia(item.get("AgenciaFechaFin")),
                    _normalizar_agencia(item.get("AgenciaFechaInicio")),
                    _normalizar_agencia(
                        item.get("AgenciaDiaAnteriorFechaFin")
                    ),
                )
                if agencia
            }
        )

        return CarteraImproductivaResponse(
            fecha_corte_fecha_fin=fecha_corte_fin,
            fecha_corte_fecha_inicio=fecha_corte_inicio,
            fecha_corte_dia_anterior_fecha_fin=fecha_corte_dia_anterior_fin,
            comparacion=comparacion,
            agencias_gerentes_oficina=self.sql_repository.obtener_gerentes_oficina(
                agencias
            ),
            faltantes_en_fecha_fin=sorted(
                str(
                    (
                        por_asesor_inicio.get(clave)
                        or por_asesor_dia_anterior[clave]
                    )["CodigoBase"]
                )
                for clave in (
                    set(por_asesor_inicio) | set(por_asesor_dia_anterior)
                )
                - set(por_asesor_fin)
            ),
            faltantes_en_fecha_inicio=sorted(
                str(
                    (
                        por_asesor_fin.get(clave)
                        or por_asesor_dia_anterior[clave]
                    )["CodigoBase"]
                )
                for clave in (
                    set(por_asesor_fin) | set(por_asesor_dia_anterior)
                )
                - set(por_asesor_inicio)
            ),
            faltantes_en_dia_anterior_fecha_fin=sorted(
                str(
                    (por_asesor_fin.get(clave) or por_asesor_inicio[clave])[
                        "CodigoBase"
                    ]
                )
                for clave in (set(por_asesor_fin) | set(por_asesor_inicio))
                - set(por_asesor_dia_anterior)
            ),
        )

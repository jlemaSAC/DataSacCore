from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cmp_to_key
from typing import Any

from fastapi import HTTPException

from app.modules.negocios.cartera_de_credito.cartera_improductiva.schemas import (
    CarteraImproductivaResponse,
    CarteraImproductivaPrestamosRequest,
    CarteraImproductivaPrestamosResponse,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.service import (
    _agrupar_por_asesor,
    _clave_usuario_agencia,
    _codigo_usuario,
    _normalizar_numero_prestamo,
    _fecha_corte,
    _filtrar_diferidos,
    _normalizar_agencia,
    _obtener_reasignaciones,
    _to_float_safe,
    _valores_normalizados,
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


def _mes_anterior(fecha: date) -> date:
    anio, mes = (fecha.year - 1, 12) if fecha.month == 1 else (fecha.year, fecha.month - 1)
    return date(anio, mes, min(fecha.day, monthrange(anio, mes)[1]))


@dataclass
class _CorteCartera:
    fecha: str
    documentos: list[dict[str, Any]]
    reasignaciones: dict[str, str]
    por_asesor: dict[str, dict[str, Any]]


def _comparacion(
    codigo: str,
    fin: dict[str, Any] | None,
    inicio: dict[str, Any] | None,
    anterior: dict[str, Any] | None,
    inicio_mes_anterior: dict[str, Any] | None = None,
    fin_mes_anterior: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = fin or inicio or anterior or fin_mes_anterior or inicio_mes_anterior or {}
    return {
        "CodigoUsuario": codigo,
        "NombreAsesorFechaFin": fin.get("NombreAsesor") if fin else None,
        "NombreAsesorFechaInicio": inicio.get("NombreAsesor") if inicio else None,
        "NombreAsesorDiaAnteriorFechaFin": anterior.get("NombreAsesor") if anterior else None,
        "NombreAsesorFechaInicioMesAnterior": inicio_mes_anterior.get("NombreAsesor") if inicio_mes_anterior else None,
        "NombreAsesorFechaFinMesAnterior": fin_mes_anterior.get("NombreAsesor") if fin_mes_anterior else None,
        "CargoAsesorFechaFin": base.get("CargoAsesor"),
        "AgenciaFechaFin": fin.get("Agencia") if fin else None,
        "AgenciaFechaInicio": inicio.get("Agencia") if inicio else None,
        "AgenciaDiaAnteriorFechaFin": anterior.get("Agencia") if anterior else None,
        "AgenciaFechaInicioMesAnterior": inicio_mes_anterior.get("Agencia") if inicio_mes_anterior else None,
        "AgenciaFechaFinMesAnterior": fin_mes_anterior.get("Agencia") if fin_mes_anterior else None,
        "ValoresFechaFin": _valores_cartera_improductiva(fin),
        "ValoresFechaInicio": _valores_cartera_improductiva(inicio),
        "ValoresDiaAnteriorFechaFin": _valores_cartera_improductiva(anterior),
        "ValoresFechaInicioMesAnterior": _valores_cartera_improductiva(inicio_mes_anterior),
        "ValoresFechaFinMesAnterior": _valores_cartera_improductiva(fin_mes_anterior),
    }


class CarteraImproductivaService:
    def __init__(
        self, mongo_repository: Any, sql_repository: Any, clientes_repository: Any = None,
    ) -> None:
        self.mongo_repository = mongo_repository
        self.sql_repository = sql_repository
        self.clientes_repository = clientes_repository

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
        inicio_corte, anterior_corte, fin_corte, inicio_mes_anterior, fin_mes_anterior = self._preparar_cortes(
            fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
            id_agencia=id_agencia, filtrar_diferidos=filtrar_diferidos, ahora=ahora,
        )
        fecha_corte_inicio = inicio_corte.fecha
        fecha_corte_dia_anterior_fin = anterior_corte.fecha
        fecha_corte_fin = fin_corte.fecha
        por_asesor_inicio = inicio_corte.por_asesor
        por_asesor_dia_anterior = anterior_corte.por_asesor
        por_asesor_fin = fin_corte.por_asesor

        claves = set().union(*(corte.por_asesor for corte in (
            inicio_corte, anterior_corte, fin_corte, inicio_mes_anterior, fin_mes_anterior,
        )))
        comparacion: list[dict[str, Any]] = []
        for clave in sorted(claves):
            fin = por_asesor_fin.get(clave)
            inicio = por_asesor_inicio.get(clave)
            dia_anterior = por_asesor_dia_anterior.get(clave)
            previo_inicio = inicio_mes_anterior.por_asesor.get(clave)
            previo_fin = fin_mes_anterior.por_asesor.get(clave)
            asesor_base = fin or inicio or dia_anterior or previo_fin or previo_inicio
            if asesor_base is None:
                continue

            comparacion.append(
                _comparacion(asesor_base["CodigoBase"], fin, inicio, dia_anterior, previo_inicio, previo_fin)
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
                    _normalizar_agencia(item.get("AgenciaFechaInicioMesAnterior")),
                    _normalizar_agencia(item.get("AgenciaFechaFinMesAnterior")),
                )
                if agencia
            }
        )

        return CarteraImproductivaResponse(
            fecha_corte_fecha_inicio_mes_anterior=inicio_mes_anterior.fecha,
            fecha_corte_fecha_fin_mes_anterior=fin_mes_anterior.fecha,
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

    def _preparar_cortes(
        self, *, fecha_inicio: date, fecha_fin: date,
        id_agencia: int, filtrar_diferidos: bool | None,
        ahora: datetime | None = None,
    ) -> tuple[_CorteCartera, _CorteCartera, _CorteCartera, _CorteCartera, _CorteCartera]:
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

        fechas = (
            fecha_corte_inicio, fecha_corte_dia_anterior_fin, fecha_corte_fin,
            _fecha_corte(_mes_anterior(fecha_inicio)),
            _fecha_corte(_mes_anterior(fecha_fin)),
        )
        documentos_por_fecha = {
            fecha: self._obtener_corte(fecha, fecha_corte_actual_disponible, agencia_nombre)
            for fecha in dict.fromkeys(fechas)
        }
        documentos_fin_sin_filtro = documentos_por_fecha[fecha_corte_fin]
        cortes = []
        for fecha in fechas:
            sin_filtro = documentos_por_fecha[fecha]
            reasignaciones = (
                {} if fecha == fecha_corte_fin else
                _obtener_reasignaciones(documentos_fin_sin_filtro, sin_filtro)
            )
            documentos = _filtrar_diferidos(sin_filtro, filtrar_diferidos)
            por_asesor = _agrupar_por_asesor(
                documentos, reasignaciones, separar_por_agencia,
                preferir_provision_calculada=fecha != fecha_corte_actual_disponible,
            )
            cortes.append(_CorteCartera(fecha, documentos, reasignaciones, por_asesor))
        return cortes[0], cortes[1], cortes[2], cortes[3], cortes[4]

    def obtener_prestamos(
        self, request: CarteraImproductivaPrestamosRequest,
        *, ahora: datetime | None = None,
    ) -> CarteraImproductivaPrestamosResponse:
        cortes = self._preparar_cortes(
            fecha_inicio=request.fecha_inicio, fecha_fin=request.fecha_fin,
            id_agencia=request.id_agencia, filtrar_diferidos=request.filtrar_diferidos,
            ahora=ahora,
        )
        separar = request.id_agencia == 0
        claves = {
            _clave_usuario_agencia(
                grupo.codigo_usuario.strip(), _normalizar_agencia(grupo.agencia), separar,
            )
            for grupo in request.grupos
        }
        disponibles = set().union(*(corte.por_asesor.keys() for corte in cortes))
        if claves - disponibles:
            raise HTTPException(
                status_code=409,
                detail="La selección ya no está disponible. Actualiza la consulta principal.",
            )

        # Seleccionar después de reasignar: los importes siguen siendo los de cada corte.
        por_prestamo: dict[str, list[list[dict[str, Any]]]] = {}
        for indice, corte in enumerate(cortes):
            for documento in corte.documentos:
                numero = _normalizar_numero_prestamo(documento.get("NumeroPrestamo"))
                codigo = corte.reasignaciones.get(numero, _codigo_usuario(documento))
                if not codigo:
                    continue
                clave = _clave_usuario_agencia(
                    codigo, _normalizar_agencia(documento.get("Agencia")), separar,
                )
                if clave not in claves:
                    continue
                if numero is None:
                    raise HTTPException(
                        status_code=409,
                        detail="Hay datos sin número de préstamo en la selección.",
                    )
                por_prestamo.setdefault(numero, [[] for _ in cortes])[indice].append(documento)

        filas: list[dict[str, Any]] = []
        for numero, documentos in por_prestamo.items():
            valores = [self._resumir_documentos(items) for items in documentos]
            inicio, anterior, fin, previo_inicio, previo_fin = valores
            base = next(items[0] for items in (documentos[2], documentos[0], documentos[1], documentos[4], documentos[3]) if items)
            codigo = cortes[2].reasignaciones.get(numero, _codigo_usuario(base))
            if not documentos[2]:
                indice_base = next(i for i in (0, 1, 4, 3) if documentos[i])
                codigo = cortes[indice_base].reasignaciones.get(numero, _codigo_usuario(base))
            fila = _comparacion(codigo or "", fin, inicio, anterior, previo_inicio, previo_fin)
            # Si el corte final pertenece a otra agencia, no se incorporan sus importes.
            fila.update({
                "NumeroPrestamo": numero,
                "NombreCliente": base.get("Nombres") or base.get("NombreCliente"),
                "NumeroSocio": str(base["Cliente"]) if base.get("Cliente") is not None else None,
            })
            filas.append(fila)

        total_seleccion = len(filas)
        totales_cortes = []
        for corte in cortes:
            asesores = [corte.por_asesor[clave] for clave in claves if clave in corte.por_asesor]
            if not asesores:
                totales_cortes.append(None)
                continue
            saldo = sum(item["Valores"]["SaldoCapital"] for item in asesores)
            improductiva = sum(item["Valores"]["CarteraImproductiva"] for item in asesores)
            mora = improductiva / saldo if saldo else 0.0
            totales_cortes.append({"Valores": {
                "SaldoCapital": round(saldo, 2), "CarteraImproductiva": round(improductiva, 2),
                "Mora": mora, "MoraPorcentaje": mora * 100,
            }})
        totales = _comparacion("TOTAL", totales_cortes[2], totales_cortes[0], totales_cortes[1], totales_cortes[3], totales_cortes[4])
        totales["NombreAsesorFechaFin"] = "TOTAL SELECCIÓN"

        if request.solo_improductivos:
            filas = [fila for fila in filas if any(
                fila[fuente] and fila[fuente]["CarteraImproductiva"] > 0
                for fuente in ("ValoresFechaInicio", "ValoresDiaAnteriorFechaFin", "ValoresFechaFin", "ValoresFechaInicioMesAnterior", "ValoresFechaFinMesAnterior")
            )]
        self._completar_clientes(filas)
        filas.sort(key=cmp_to_key(lambda a, b: self._comparar_filas(a, b, request)))
        total_resultados = len(filas)
        return CarteraImproductivaPrestamosResponse(
            fecha_corte_fecha_inicio_mes_anterior=cortes[3].fecha,
            fecha_corte_fecha_fin_mes_anterior=cortes[4].fecha,
            fecha_corte_fecha_inicio=cortes[0].fecha,
            fecha_corte_dia_anterior_fecha_fin=cortes[1].fecha,
            fecha_corte_fecha_fin=cortes[2].fecha,
            prestamos=filas, totales=totales, total_seleccion=total_seleccion,
            total_resultados=total_resultados,
        )

    @staticmethod
    def _resumir_documentos(documentos: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not documentos:
            return None
        resultado = dict(documentos[0])
        resultado["Valores"] = _valores_normalizados({
            campo: sum(_to_float_safe(documento.get(campo)) for documento in documentos)
            for campo in ("SaldoCapital", "CapitalNoDevenga", "CapitalVencido")
        })
        return resultado

    def _completar_clientes(self, filas: list[dict[str, Any]]) -> None:
        if not filas or self.clientes_repository is None:
            return
        clientes = self.clientes_repository.obtener_clientes([fila["NumeroPrestamo"] for fila in filas])
        for fila in filas:
            cliente = clientes.get(fila["NumeroPrestamo"], {})
            for campo in ("NombreCliente", "NumeroSocio"):
                if not fila.get(campo):
                    fila[campo] = cliente.get(campo) or None

    @staticmethod
    def _valor_orden(fila: dict[str, Any], campo: str) -> str | float | None:
        if campo in {"numero_prestamo", "nombre_cliente"}:
            return str(fila.get("NumeroPrestamo" if campo == "numero_prestamo" else "NombreCliente") or "").casefold()
        if campo in {"nombre", "agencia"}:
            prefijo = "NombreAsesor" if campo == "nombre" else "Agencia"
            return str(next((fila[prefijo + corte] for corte in (
                "FechaFin", "FechaInicio", "DiaAnteriorFechaFin",
            ) if fila.get(prefijo + corte)), "")).casefold()
        if "__" in campo:
            fuente, metrica = campo.split("__")
            return fila[fuente][metrica] if fila[fuente] is not None else None
        referencia = "ValoresDiaAnteriorFechaFin" if campo in {
            "variacionDiaAnterior", "variacionMorosidadDiaAnterior",
        } else "ValoresFechaInicio"
        fin, previo = fila["ValoresFechaFin"], fila[referencia]
        if campo.startswith("variacionMorosidad"):
            return round(fin["MorosidadPorcentaje"] - previo["MorosidadPorcentaje"], 2) if fin and previo else None
        return (fin["CarteraImproductiva"] if fin else 0) - (previo["CarteraImproductiva"] if previo else 0)

    @classmethod
    def _comparar_filas(
        cls, a: dict[str, Any], b: dict[str, Any], request: CarteraImproductivaPrestamosRequest,
    ) -> int:
        primero = cls._valor_orden(a, request.orden_por)
        segundo = cls._valor_orden(b, request.orden_por)
        if primero is None or segundo is None:
            comparacion = (primero is None) - (segundo is None)
        else:
            comparacion = ((primero > segundo) - (primero < segundo)) * request.orden
        return comparacion or ((a["NumeroPrestamo"] > b["NumeroPrestamo"]) - (a["NumeroPrestamo"] < b["NumeroPrestamo"]))

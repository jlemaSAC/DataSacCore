from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from app.modules.negocios.cartera_de_credito.matriz_transicion.schemas import (
    MatrizTransicionAsesorFiltro,
    MatrizTransicionFiltrosRequest,
    MatrizTransicionFiltrosResponse,
    MatrizTransicionPrestamosRequest,
    MatrizTransicionRequest,
    MatrizTransicionResponse,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.domain import (
    DetalleCuotaPrestamo,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.schemas import (
    GaranteRecaudacion,
    InformacionPersonaRecaudacion,
    PrestamoRecaudadoAcumulado,
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


def _normalizar_calificacion(value: Any) -> str:
    return _normalizar(value).replace("-", "").replace(" ", "")


def _variantes_calificacion(value: str) -> list[str]:
    original = _normalizar(value)
    sin_separadores = _normalizar_calificacion(value)
    if (
        len(sin_separadores) == 2
        and sin_separadores[0].isalpha()
        and sin_separadores[1].isdigit()
    ):
        return list(
            dict.fromkeys(
                (original, sin_separadores, f"{sin_separadores[0]}-{sin_separadores[1]}")
            )
        )
    return [original]


def _a_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return _normalizar(value) in {"1", "TRUE", "T", "SI", "SÍ", "S", "YES", "Y"}


def _to_int(value: Any) -> int:
    try:
        return int(_to_float(value))
    except (TypeError, ValueError):
        return 0


def _to_optional_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(_to_float(value))
    except (TypeError, ValueError):
        return None


def _texto(value: Any, default: str = "") -> str:
    texto = str(value or "").strip()
    return texto or default


def _a_fecha(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    texto = value.strip()
    for formato in ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).date()
    except ValueError:
        return None


class MatrizTransicionService:
    def __init__(self, mongo_repository: Any, sql_repository: Any | None = None) -> None:
        self.mongo_repository = mongo_repository
        self.sql_repository = sql_repository

    def obtener(
        self,
        request: MatrizTransicionRequest,
        *,
        hoy: date | None = None,
    ) -> MatrizTransicionResponse:
        (
            anterior,
            nuevo,
            fecha_anterior,
            fecha_nuevo,
            fuente_nuevo,
        ) = self._obtener_cortes(request, hoy=hoy)
        return self._construir_matriz(
            anterior=anterior,
            nuevo=nuevo,
            request=request,
            fecha_anterior=fecha_anterior,
            fecha_nuevo=fecha_nuevo,
            fuente_nuevo=fuente_nuevo,
        )

    def obtener_filtros(
        self,
        request: MatrizTransicionFiltrosRequest,
        *,
        hoy: date | None = None,
    ) -> MatrizTransicionFiltrosResponse:
        """Obtiene los catálogos disponibles en el mismo origen del corte nuevo."""
        fecha_corte = request.fecha_corte
        fecha_corte_str = _fecha_corte(fecha_corte)
        agencias = self._valores_filtro(request.agencia)

        if fecha_corte == (hoy or datetime.now().date()):
            documentos = self.mongo_repository.obtener_catalogo_actual(agencias=agencias)
            fuente = "SituacionCrediticiaActual"
        else:
            documentos = self.mongo_repository.obtener_catalogo_historico(
                fecha_corte_str,
                agencias=agencias,
            )
            fuente = "SituacionCrediticia"

        asesores: dict[tuple[str, str, str, str], MatrizTransicionAsesorFiltro] = {}
        cargos: set[str] = set()
        estados: set[str] = set()
        for documento in documentos:
            codigo = self._primer_texto(
                documento,
                "CodigoAsesor",
                "CodigoUsuario",
                "CODIGOUSUARIO",
            )
            nombre = self._primer_texto(documento, "NombreAsesor", "NombreCompleto")
            cargo = self._primer_texto(documento, "CargoAsesor")
            agencia = self._primer_texto(documento, "Agencia")
            estado = self._primer_texto(
                documento,
                "EstadoPrestamo",
                "CodigoEstadoPrestamo",
                "CodigoEstado",
            )

            if cargo:
                cargos.add(cargo)
            if estado:
                estados.add(estado)
            if codigo or nombre:
                item = MatrizTransicionAsesorFiltro(
                    codigo=codigo,
                    nombre=nombre,
                    cargo=cargo,
                    agencia=agencia,
                )
                asesores[(codigo, nombre, cargo, agencia)] = item

        return MatrizTransicionFiltrosResponse(
            fecha_corte=fecha_corte_str,
            fuente=fuente,
            asesores=sorted(
                asesores.values(),
                key=lambda item: (
                    item.agencia.casefold(),
                    item.nombre.casefold(),
                    item.codigo.casefold(),
                ),
            ),
            cargos=sorted(cargos, key=str.casefold),
            estados_prestamo=sorted(estados, key=str.casefold),
        )

    def obtener_prestamos(
        self,
        request: MatrizTransicionPrestamosRequest,
        *,
        hoy: date | None = None,
    ) -> list[PrestamoRecaudadoAcumulado]:
        """Devuelve los préstamos de una transición y su detalle de cuotas."""
        if self.sql_repository is None:
            raise RuntimeError("El servicio de detalle de cuotas no está configurado.")
        anterior, nuevo, _, _, _ = self._obtener_cortes(
            request,
            hoy=hoy,
            calificacion_nueva=_variantes_calificacion(request.calificacion_nueva),
            incluir_detalle=True,
        )
        anterior_por_prestamo = self._indexar(
            anterior,
            lado="anterior",
            request=request,
        )
        nuevo_por_prestamo = self._indexar(nuevo, lado="nuevo", request=request)
        calificacion_anterior = _normalizar_calificacion(request.calificacion_anterior)
        calificacion_nueva = _normalizar_calificacion(request.calificacion_nueva)

        seleccionados: list[tuple[str, dict[str, Any] | None, dict[str, Any]]] = []
        for numero, actual in nuevo_por_prestamo.items():
            if _normalizar_calificacion(actual["calificacion"]) != calificacion_nueva:
                continue
            previo = anterior_por_prestamo.get(numero)
            if calificacion_anterior == "NA":
                if previo is None:
                    seleccionados.append((numero, None, actual["documento"]))
            elif (
                previo
                and _normalizar_calificacion(previo["calificacion"])
                == calificacion_anterior
            ):
                seleccionados.append((numero, previo["documento"], actual["documento"]))

        detalles = self.sql_repository.obtener_detalles(
            [
                {
                    "numero_prestamo": numero,
                    "provision_actual": self._valor_metrica(actual, "ProvisionRequerida"),
                    "saldo_actual": self._valor_metrica(actual, "SaldoCapital"),
                }
                for numero, _, actual in seleccionados
            ]
        )
        return [
            self._construir_prestamo(
                numero=numero,
                anterior=previo,
                nuevo=actual,
                detalle=detalles.get(numero),
            )
            for numero, previo, actual in sorted(seleccionados, key=lambda item: item[0])
        ]

    def _obtener_cortes(
        self,
        request: MatrizTransicionRequest,
        *,
        hoy: date | None,
        calificacion_nueva: str | list[str] | None = None,
        incluir_detalle: bool = False,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, str, str]:
        fecha_anterior = request.fecha_corte_anterior.date()
        fecha_fin = request.fecha_corte_nuevo.date()
        fecha_anterior_str = _fecha_corte(fecha_anterior)
        fecha_fin_str = _fecha_corte(fecha_fin)
        filtros_nuevo = self._filtros_nuevo(request)
        filtros_nuevo["calificacion"] = calificacion_nueva

        if fecha_fin == (hoy or datetime.now().date()):
            nuevo = self.mongo_repository.obtener_actual_filtrado(
                **filtros_nuevo,
                incluir_detalle=incluir_detalle,
            )
            fuente_nuevo = "SituacionCrediticiaActual"
        else:
            nuevo = self.mongo_repository.obtener_historico_filtrado(
                fecha_fin_str,
                **filtros_nuevo,
                incluir_detalle=incluir_detalle,
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
            incluir_detalle=incluir_detalle,
        )
        prestamos_cancelados_anterior = {
            str(document.get("NumeroPrestamo") or "").strip()
            for document in anterior
            if self._es_cancelado(document)
        }
        if prestamos_cancelados_anterior:
            nuevo = [
                document
                for document in nuevo
                if str(document.get("NumeroPrestamo") or "").strip()
                not in prestamos_cancelados_anterior
            ]
        return anterior, nuevo, fecha_anterior_str, fecha_fin_str, fuente_nuevo

    @staticmethod
    def _filtros_nuevo(request: MatrizTransicionRequest) -> dict[str, Any]:
        return {
            "agencias": MatrizTransicionService._valores_filtro(request.agencia),
            "diferido": request.diferido,
            "cargos": MatrizTransicionService._valores_filtro(request.cargo),
            "estados": MatrizTransicionService._valores_filtro(request.estado_prestamo),
            "asesores": MatrizTransicionService._valores_filtro(request.asesores),
        }

    @staticmethod
    def _valores_filtro(value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        items = value if isinstance(value, list) else [value]
        return [str(item).strip() for item in items if str(item).strip()]

    @staticmethod
    def _primer_texto(documento: dict[str, Any], *campos: str) -> str:
        for campo in campos:
            valor = _texto(documento.get(campo))
            if valor:
                return valor
        return ""

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

    def _construir_prestamo(
        self,
        *,
        numero: str,
        anterior: dict[str, Any] | None,
        nuevo: dict[str, Any],
        detalle: DetalleCuotaPrestamo | None,
    ) -> PrestamoRecaudadoAcumulado:
        anterior = anterior or {}
        detalle = detalle or DetalleCuotaPrestamo(numero_prestamo=numero)
        personal = (
            nuevo if nuevo.get("Nombres") or nuevo.get("NombreCliente") else anterior
        )
        dias_anterior = _to_int(anterior.get("DiasVencidos"))
        dias_actual = _to_int(nuevo.get("DiasVencidos"))
        saldo_anterior = _to_float(anterior.get("SaldoCapital"))
        saldo_actual = _to_float(nuevo.get("SaldoCapital"))
        provision_anterior = self._valor_metrica(anterior, "ProvisionRequerida")
        provision_actual = self._valor_metrica(nuevo, "ProvisionRequerida")
        gasto_cobranza = _to_float(nuevo.get("GastoCobranza"))
        cancelado = self._es_cancelado(nuevo)

        informacion_deudor = None
        garante_1 = None
        garante_2 = None
        if not cancelado:
            informacion_deudor = InformacionPersonaRecaudacion(
                identificacion=_texto(
                    personal.get("Identificacion"),
                    detalle.identificacion,
                ),
                provincia=_texto(personal.get("Provincia"), detalle.provincia),
                canton=_texto(personal.get("Canton"), detalle.canton),
                parroquia=_texto(personal.get("Parroquia"), detalle.parroquia),
                direccion=_texto(personal.get("Direccion"), detalle.direccion),
                telefonos=_texto(personal.get("Telefonos"), detalle.telefonos),
            )
            garante_1 = self._construir_garante(personal, "G1_", detalle.garante_1)
            garante_2 = self._construir_garante(personal, "G2_", detalle.garante_2)

        provision_con_cobro = self._calcular_provision_con_cobro(
            detalle=detalle,
            provision_actual=provision_actual,
            saldo_actual=saldo_actual,
        )

        return PrestamoRecaudadoAcumulado(
            socio=_to_optional_int(
                personal.get("Cliente", personal.get("NumeroCliente"))
            ) or detalle.socio,
            agencia=_texto(nuevo.get("Agencia")),
            numero_prestamo=numero,
            codigo_usuario_asignado=_texto(
                nuevo.get(
                    "CodigoAsesor",
                    nuevo.get("CodigoUsuario", nuevo.get("CODIGOUSUARIO")),
                )
            ),
            nombre_usuario_asignado=_texto(
                nuevo.get("NombreAsesor", nuevo.get("NombreCompleto")), "SIN ASESOR"
            ),
            nombre=_texto(
                personal.get("Nombres", personal.get("NombreCliente")),
                detalle.nombre,
            ),
            estado_anterior=_texto(anterior.get("EstadoPrestamo"), "NO EXISTIA"),
            estado_actual=_texto(nuevo.get("EstadoPrestamo"), "SIN DATOS"),
            calificacion_anterior=_texto(anterior.get("Calificacion"), "NO EXISTIA"),
            calificacion_actual=_texto(nuevo.get("Calificacion"), "SIN DATOS"),
            dias_mora_anterior=dias_anterior,
            dias_mora_actual=dias_actual,
            variacion_dias_mora=dias_actual - dias_anterior,
            saldo_capital_anterior=round(saldo_anterior, 2),
            saldo_capital_actual=round(saldo_actual, 2),
            variacion_saldo_capital=round(saldo_actual - saldo_anterior, 2),
            numero_cuota_actual_no_pagada=detalle.numero_cuota_actual_no_pagada,
            numero_cuota_siguiente=detalle.numero_cuota_siguiente,
            cobro_para_bajar_una_cuota=round(
                detalle.cobro_hasta_cuota + gasto_cobranza,
                2,
            ),
            cuotas_pendientes=detalle.cuotas_pendientes,
            cuotas_pagadas=detalle.cuotas_pagadas,
            total_cuotas=detalle.total_cuotas or _to_int(nuevo.get("Plazo")),
            calificacion_con_cobro_una_cuota=_texto(
                detalle.calificacion_con_cobro_una_cuota,
                "A-1",
            ),
            dias_mora_con_cobro_una_cuota=detalle.dias_mora_con_cobro_una_cuota,
            saldo_capital_con_cobro_una_cuota=round(
                detalle.saldo_capital_con_cobro_una_cuota,
                2,
            ),
            provision_con_cobro_una_cuota=provision_con_cobro,
            provision_cierre_mes=round(provision_anterior, 2),
            provision_actual=round(provision_actual, 2),
            variacion_provisiones=round(provision_actual - provision_anterior, 2),
            dia_ultimo_pago=_a_fecha(
                nuevo.get("FechaUltimoPago", nuevo.get("UltimoPago"))
            ),
            total_recuperado=0.0,
            pendiente_pago=round(
                _to_float(nuevo.get("ValorParaEstarAlDia")) + gasto_cobranza,
                2,
            ),
            pendiente_pago_mas_cuota_por_vencer=round(
                _to_float(nuevo.get("ValorHastaCuotaActual")) + gasto_cobranza, 2
            ),
            total_a_cancelar=round(
                _to_float(nuevo.get("ValorCancelarTotal")) + gasto_cobranza,
                2,
            ),
            informacion_deudor=informacion_deudor,
            garante_1=garante_1,
            garante_2=garante_2,
        )

    @staticmethod
    def _construir_garante(
        document: dict[str, Any],
        prefijo: str,
        fallback: dict[str, str] | None,
    ) -> GaranteRecaudacion | None:
        fallback = fallback or {}
        nombres = _texto(document.get(f"{prefijo}Nombres"), fallback.get("nombres", ""))
        identificacion = _texto(
            document.get(f"{prefijo}Identificacion"),
            fallback.get("identificacion", ""),
        )
        if not nombres and not identificacion:
            return None
        return GaranteRecaudacion(
            nombres=nombres,
            identificacion=identificacion,
            provincia=_texto(document.get(f"{prefijo}Provincia"), fallback.get("provincia", "")),
            canton=_texto(document.get(f"{prefijo}Canton"), fallback.get("canton", "")),
            parroquia=_texto(document.get(f"{prefijo}Parroquia"), fallback.get("parroquia", "")),
            direccion=_texto(document.get(f"{prefijo}Direccion"), fallback.get("direccion", "")),
            telefonos=_texto(document.get(f"{prefijo}Telefonos"), fallback.get("telefonos", "")),
        )

    @staticmethod
    def _calcular_provision_con_cobro(
        *,
        detalle: DetalleCuotaPrestamo,
        provision_actual: float,
        saldo_actual: float,
    ) -> float:
        saldo_simulado = max(detalle.saldo_capital_con_cobro_una_cuota, 0.0)
        if saldo_simulado == 0:
            return 0.0
        if detalle.es_porcentaje_fijo is True:
            porcentaje = detalle.porcentaje_fijo or 0.0
        elif detalle.es_porcentaje_fijo is not None:
            porcentaje = (provision_actual / saldo_actual * 100) if saldo_actual > 0 else 0.0
            if detalle.porcentaje_minimo is not None:
                porcentaje = max(porcentaje, detalle.porcentaje_minimo)
            if detalle.porcentaje_maximo not in (None, 0):
                porcentaje = min(porcentaje, detalle.porcentaje_maximo)
        else:
            porcentaje = (provision_actual / saldo_actual * 100) if saldo_actual > 0 else 0.0
        return round(saldo_simulado * porcentaje / 100, 2)

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

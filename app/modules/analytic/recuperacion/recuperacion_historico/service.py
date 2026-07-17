import logging
from datetime import date, datetime
from time import perf_counter
from typing import Any

from fastapi import HTTPException

from app.modules.analytic.recuperacion.recuperacion_historico.domain import (
    PrestamoRecuperacion,
    RecuperacionEtiquetada,
)
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.mongo_recuperacion_historico_repository import (
    MongoRecuperacionHistoricoRepository,
)
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.sql_recuperacion_historico_repository import (
    SqlRecuperacionHistoricoRepository,
)
from app.modules.analytic.recuperacion.recuperacion_historico.schemas import (
    InputRecuperacionHistoricoAgrupado,
    InputRecuperacionHistoricoRango,
    RecuperacionCatalogosOut,
    RecuperacionEtiquetadaOut,
    RecuperacionHistoricoAgrupadoResponse,
    RecuperacionHistoricoCompactoResponse,
    RecuperacionHistoricoRangoResponse,
    RecuperacionPeriodoOut,
    RecuperacionResumenAgrupadoOut,
    RecuperacionResumenCompactoOut,
    RecuperacionSerieOut,
    RecuperacionCatalogosCompactosOut,
    PrestamoRecuperacionOut,
)
from app.modules.auth.schemas import AuthContext


logger = logging.getLogger("uvicorn.error")
MAX_MESES_RANGO = 60
MESES = (
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
)


class RecuperacionHistoricoService:
    def __init__(
        self,
        mongo_repository: MongoRecuperacionHistoricoRepository,
        sql_repository: SqlRecuperacionHistoricoRepository | None = None,
    ) -> None:
        self.mongo_repository = mongo_repository
        self.sql_repository = sql_repository

    def obtener_recuperacion_por_rango(
        self,
        input_data: InputRecuperacionHistoricoRango,
        auth_context: AuthContext,
    ) -> RecuperacionHistoricoRangoResponse:
        try:
            fecha_sistema = auth_context.usuario.fecha_sistema
            fecha_hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
            self._validar_rango(input_data, fecha_hoy)

            inicio_mongo = perf_counter()
            recuperaciones = self.mongo_repository.obtener_recuperaciones(input_data, fecha_hoy)
            print(f"[recuperacion][service] mongo_total_ms={(perf_counter() - inicio_mongo) * 1000:.2f}")
            inicio_prestamos = perf_counter()
            numeros_prestamo = {
                recuperacion.numero_prestamo
                for recuperacion in recuperaciones
                if recuperacion.numero_prestamo
            }
            prestamos_por_numero = self.mongo_repository.obtener_prestamos_por_numero(
                numeros_prestamo,
                input_data.fecha_desde.strftime("%Y%m%d"),
                input_data.fecha_hasta.strftime("%Y%m%d"),
                fecha_hoy.strftime("%Y%m%d"),
            )
            print(
                "[recuperacion][service] prestamos_total_ms="
                f"{(perf_counter() - inicio_prestamos) * 1000:.2f} prestamos={len(prestamos_por_numero)}"
            )
            inicio_respuesta = perf_counter()
            respuesta = self._construir_respuesta(input_data, recuperaciones, prestamos_por_numero)
            print(
                "[recuperacion][service] respuesta_ms="
                f"{(perf_counter() - inicio_respuesta) * 1000:.2f} recuperaciones={len(recuperaciones)}"
            )
            return respuesta
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error consultando recuperacion en Mongo")
            raise HTTPException(status_code=500, detail=f"Error consultando recuperacion: {exc}") from exc

    def obtener_recuperacion_agrupada(
        self,
        input_data: InputRecuperacionHistoricoAgrupado,
        auth_context: AuthContext,
    ) -> RecuperacionHistoricoAgrupadoResponse:
        try:
            fecha_sistema = auth_context.usuario.fecha_sistema
            fecha_hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
            self._validar_rango(input_data, fecha_hoy)
            inicio = perf_counter()
            resultado = self.mongo_repository.obtener_recuperacion_agrupada(
                input_data,
                fecha_hoy,
            )
            respuesta = self._construir_respuesta_agrupada(input_data, resultado)
            print(
                "[recuperacion][service][agrupado] "
                f"dimension={input_data.dimension} series={len(respuesta.series)} "
                f"periodos={len(respuesta.periodos)} "
                f"total_ms={(perf_counter() - inicio) * 1000:.2f}"
            )
            return respuesta
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error consultando recuperacion agrupada en Mongo")
            raise HTTPException(
                status_code=500,
                detail=f"Error consultando recuperacion agrupada: {exc}",
            ) from exc

    def obtener_recuperacion_compacta(
        self,
        input_data: InputRecuperacionHistoricoRango,
        auth_context: AuthContext,
    ) -> RecuperacionHistoricoCompactoResponse:
        try:
            fecha_sistema = auth_context.usuario.fecha_sistema
            fecha_hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
            self._validar_rango(input_data, fecha_hoy)
            recuperaciones = self.mongo_repository.obtener_recuperaciones(input_data, fecha_hoy)
            numeros_prestamo = {
                recuperacion.numero_prestamo
                for recuperacion in recuperaciones
                if recuperacion.numero_prestamo
            }
            prestamos_por_numero = self.mongo_repository.obtener_prestamos_por_numero(
                numeros_prestamo,
                input_data.fecha_desde.strftime("%Y%m%d"),
                input_data.fecha_hasta.strftime("%Y%m%d"),
                fecha_hoy.strftime("%Y%m%d"),
            )
            respuesta = self._construir_respuesta_compacta(
                input_data,
                recuperaciones,
                prestamos_por_numero,
            )
            print(
                "[recuperacion][service][compacto] "
                f"prestamos={respuesta.resumen.cantidad_prestamos} "
                f"recuperaciones={respuesta.resumen.cantidad_recuperaciones}"
            )
            return respuesta
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error consultando recuperacion compacta en Mongo")
            raise HTTPException(
                status_code=500,
                detail=f"Error consultando recuperacion compacta: {exc}",
            ) from exc

    @staticmethod
    def _validar_rango(
        input_data: InputRecuperacionHistoricoRango,
        fecha_hoy: date,
    ) -> None:
        if input_data.fecha_hasta > fecha_hoy:
            raise HTTPException(400, "fecha_hasta no puede ser posterior a la fecha del sistema.")
        meses = (
            (input_data.fecha_hasta.year - input_data.fecha_desde.year) * 12
            + input_data.fecha_hasta.month
            - input_data.fecha_desde.month
            + 1
        )
        if meses > MAX_MESES_RANGO:
            raise HTTPException(400, f"El rango no puede superar {MAX_MESES_RANGO} meses.")

    @staticmethod
    def _construir_respuesta_agrupada(
        input_data: InputRecuperacionHistoricoAgrupado,
        resultado: dict[str, Any],
    ) -> RecuperacionHistoricoAgrupadoResponse:
        filas = resultado.get("datos", [])
        claves_periodo = sorted({str(fila["periodo"]) for fila in filas})
        indices = {clave: indice for indice, clave in enumerate(claves_periodo)}
        series_map: dict[str, dict] = {}
        cantidad_movimientos = 0
        for fila in filas:
            etiqueta = str(fila.get("etiqueta") or "SIN DATOS")
            serie = series_map.setdefault(
                etiqueta,
                {
                    "valores": [0.0] * len(claves_periodo),
                    "total": 0.0,
                },
            )
            valor = float(fila.get("valor") or 0)
            serie["valores"][indices[str(fila["periodo"])]] += valor
            serie["total"] += valor
            cantidad_movimientos += int(fila.get("cantidad_movimientos") or 0)

        series = sorted(
            (
                RecuperacionSerieOut(
                    clave=etiqueta,
                    etiqueta=etiqueta,
                    valores=datos["valores"],
                    total=datos["total"],
                )
                for etiqueta, datos in series_map.items()
            ),
            key=lambda serie: (-serie.total, serie.etiqueta),
        )
        totales_por_periodo = [
            sum(serie.valores[indice] for serie in series)
            for indice in range(len(claves_periodo))
        ]
        return RecuperacionHistoricoAgrupadoResponse(
            dimension=input_data.dimension,
            periodos=[_periodo_out(clave) for clave in claves_periodo],
            series=series,
            totales_por_periodo=totales_por_periodo,
            total_general=sum(totales_por_periodo),
            catalogos=RecuperacionCatalogosOut(
                agencias=resultado.get("agencias", []),
                asesores=resultado.get("asesores", []),
                tipos_prestamo=resultado.get("tipos_prestamo", []),
            ),
            resumen=RecuperacionResumenAgrupadoOut(
                cantidad_movimientos=cantidad_movimientos,
                cantidad_series=len(series),
            ),
        )

    @staticmethod
    def _construir_respuesta(
        input_data: InputRecuperacionHistoricoRango,
        recuperaciones: list[RecuperacionEtiquetada],
        prestamos_por_numero: dict[str, PrestamoRecuperacion],
    ) -> RecuperacionHistoricoRangoResponse:
        datos: list[RecuperacionEtiquetadaOut] = []
        for recuperacion in recuperaciones:
            prestamo_actual = prestamos_por_numero.get(recuperacion.numero_prestamo)
            datos.append(
                RecuperacionEtiquetadaOut(
                    anio=recuperacion.fecha_cobro.year,
                    mes=recuperacion.fecha_cobro.month,
                    numero_prestamo=recuperacion.numero_prestamo,
                    tipo_cobro=recuperacion.tipo_cobro,
                    transaccion=recuperacion.tipo_transaccion,
                    valor=recuperacion.valor_recuperado,
                    agencia=_valor_contexto(recuperacion.agencia, prestamo_actual, "agencia"),
                    asesor=_valor_contexto(recuperacion.asesor, prestamo_actual, "asesor"),
                    abogado_externo=_texto_opcional(recuperacion.abogado_externo),
                    nombre_cobranza_apoyo=_texto_opcional(recuperacion.nombre_cobranza_apoyo),
                    estado_anterior=_valor_contexto(
                        recuperacion.estado_prestamo_anterior_cobro,
                        prestamo_actual,
                        "estado_prestamo_inicio",
                    ),
                    estado_actual=_valor_contexto(
                        recuperacion.estado_prestamo_actual_cobro,
                        prestamo_actual,
                        "estado_prestamo_fin",
                    ),
                    calificacion_anterior=_valor_contexto(
                        recuperacion.calificacion_anterior_cobro,
                        prestamo_actual,
                        "calificacion_inicio",
                    ),
                    calificacion_actual=_valor_contexto(
                        recuperacion.calificacion_actual_cobro,
                        prestamo_actual,
                        "calificacion_fin",
                    ),
                )
            )

        return RecuperacionHistoricoRangoResponse(
            prestamos_por_numero={
                numero: PrestamoRecuperacionOut(**prestamo.__dict__)
                for numero, prestamo in prestamos_por_numero.items()
            },
            recuperaciones=datos,
        )

    @staticmethod
    def _construir_respuesta_compacta(
        input_data: InputRecuperacionHistoricoRango,
        recuperaciones: list[RecuperacionEtiquetada],
        prestamos_por_numero: dict[str, PrestamoRecuperacion],
    ) -> RecuperacionHistoricoCompactoResponse:
        catalogos = _CatalogosCompactos()
        filas_prestamo: list[list[str | int]] = []
        indice_prestamo: dict[str, int] = {}
        prestamos_respuesta = {
            numero: prestamos_por_numero.get(numero, _prestamo_sin_datos(numero))
            for numero in {recuperacion.numero_prestamo for recuperacion in recuperaciones}
        }
        for numero, prestamo in sorted(prestamos_respuesta.items()):
            indice_prestamo[numero] = len(filas_prestamo)
            filas_prestamo.append(
                [
                    numero,
                    catalogos.indice("agencias", prestamo.agencia),
                    catalogos.indice("condiciones", prestamo.condicion),
                    catalogos.indice("tipos_prestamo", prestamo.tipo_prestamo),
                    catalogos.indice("productos", prestamo.producto),
                    catalogos.indice("segmentos", prestamo.segmento),
                    catalogos.indice("asesores", prestamo.asesor),
                    catalogos.indice("provincias", prestamo.provincia),
                    catalogos.indice("cantones", prestamo.canton),
                    catalogos.indice("parroquias", prestamo.parroquia),
                    catalogos.indice("educaciones", prestamo.educacion),
                    prestamo.edad if prestamo.edad is not None else -1,
                    catalogos.indice("garantias", prestamo.garantia),
                    _centavos(prestamo.monto),
                    _centenas(prestamo.tasa),
                    _centenas(prestamo.tasa_real),
                    prestamo.plazo if prestamo.plazo is not None else -1,
                    catalogos.indice("estados_prestamo", prestamo.estado_prestamo_inicio),
                    catalogos.indice("estados_prestamo", prestamo.estado_prestamo_fin),
                    catalogos.indice("calificaciones", prestamo.calificacion_inicio),
                    catalogos.indice("calificaciones", prestamo.calificacion_fin),
                ]
            )

        periodos: list[str] = []
        indice_periodo: dict[str, int] = {}
        filas_recuperacion: list[list[int]] = []
        for recuperacion in recuperaciones:
            prestamo_actual = prestamos_respuesta[recuperacion.numero_prestamo]
            periodo = f"{recuperacion.fecha_cobro.year:04d}-{recuperacion.fecha_cobro.month:02d}"
            periodo_id = indice_periodo.setdefault(periodo, len(periodos))
            if periodo_id == len(periodos):
                periodos.append(periodo)
            filas_recuperacion.append(
                [
                    periodo_id,
                    indice_prestamo[recuperacion.numero_prestamo],
                    catalogos.indice("tipos_cobro", recuperacion.tipo_cobro),
                    catalogos.indice("tipos_transaccion", recuperacion.tipo_transaccion),
                    _centavos(recuperacion.valor_recuperado),
                    catalogos.indice(
                        "agencias",
                        _valor_contexto(recuperacion.agencia, prestamo_actual, "agencia"),
                    ),
                    catalogos.indice(
                        "asesores",
                        _valor_contexto(recuperacion.asesor, prestamo_actual, "asesor"),
                    ),
                    catalogos.indice("abogados_externos", recuperacion.abogado_externo),
                    catalogos.indice(
                        "nombres_cobranza_apoyo", recuperacion.nombre_cobranza_apoyo
                    ),
                    catalogos.indice(
                        "estados_prestamo",
                        _valor_contexto(
                            recuperacion.estado_prestamo_anterior_cobro,
                            prestamo_actual,
                            "estado_prestamo_inicio",
                        ),
                    ),
                    catalogos.indice(
                        "estados_prestamo",
                        _valor_contexto(
                            recuperacion.estado_prestamo_actual_cobro,
                            prestamo_actual,
                            "estado_prestamo_fin",
                        ),
                    ),
                    catalogos.indice(
                        "calificaciones",
                        _valor_contexto(
                            recuperacion.calificacion_anterior_cobro,
                            prestamo_actual,
                            "calificacion_inicio",
                        ),
                    ),
                    catalogos.indice(
                        "calificaciones",
                        _valor_contexto(
                            recuperacion.calificacion_actual_cobro,
                            prestamo_actual,
                            "calificacion_fin",
                        ),
                    ),
                ]
            )

        return RecuperacionHistoricoCompactoResponse(
            periodos=periodos,
            catalogos=catalogos.respuesta(),
            prestamos=filas_prestamo,
            recuperaciones=filas_recuperacion,
            resumen=RecuperacionResumenCompactoOut(
                cantidad_prestamos=len(filas_prestamo),
                cantidad_recuperaciones=len(filas_recuperacion),
            ),
        )


def _valor_contexto(
    valor: str,
    prestamo: PrestamoRecuperacion | None,
    atributo: str,
) -> str:
    if valor != "SIN DATOS" or prestamo is None:
        return valor
    return str(getattr(prestamo, atributo) or "SIN DATOS")


def _texto_opcional(valor: str) -> str | None:
    return None if valor == "SIN DATOS" else valor


class _CatalogosCompactos:
    _CAMPOS = (
        "agencias",
        "condiciones",
        "tipos_prestamo",
        "productos",
        "segmentos",
        "asesores",
        "provincias",
        "cantones",
        "parroquias",
        "educaciones",
        "garantias",
        "estados_prestamo",
        "calificaciones",
        "tipos_cobro",
        "tipos_transaccion",
        "abogados_externos",
        "nombres_cobranza_apoyo",
    )

    def __init__(self) -> None:
        self.valores = {campo: [] for campo in self._CAMPOS}
        self.indices = {campo: {} for campo in self._CAMPOS}

    def indice(self, campo: str, valor: str) -> int:
        texto = str(valor or "SIN DATOS")
        indice = self.indices[campo].get(texto)
        if indice is not None:
            return indice
        indice = len(self.valores[campo])
        self.indices[campo][texto] = indice
        self.valores[campo].append(texto)
        return indice

    def respuesta(self) -> RecuperacionCatalogosCompactosOut:
        return RecuperacionCatalogosCompactosOut(**self.valores)


def _centavos(valor: float | None) -> int:
    return -1 if valor is None else int(round(valor * 100))


def _centenas(valor: float | None) -> int:
    return -1 if valor is None else int(round(valor * 100))


def _prestamo_sin_datos(numero_prestamo: str) -> PrestamoRecuperacion:
    return PrestamoRecuperacion(
        numero_prestamo=numero_prestamo,
        agencia="SIN DATOS",
        condicion="SIN DATOS",
        tipo_prestamo="SIN DATOS",
        producto="SIN DATOS",
        segmento="SIN DATOS",
        asesor="SIN DATOS",
        provincia="SIN DATOS",
        canton="SIN DATOS",
        parroquia="SIN DATOS",
        educacion="SIN DATOS",
        edad=None,
        garantia="SIN DATOS",
        monto=None,
        tasa=None,
        tasa_real=None,
        plazo=None,
        estado_prestamo_inicio="SIN DATOS",
        estado_prestamo_fin="SIN DATOS",
        calificacion_inicio="SIN DATOS",
        calificacion_fin="SIN DATOS",
    )


def _periodo_out(clave: str) -> RecuperacionPeriodoOut:
    anio = int(clave[:4])
    mes = int(clave[4:6])
    return RecuperacionPeriodoOut(
        clave=f"{anio:04d}-{mes:02d}",
        anio=anio,
        mes=mes,
        etiqueta=f"{MESES[mes - 1]} {anio}",
    )

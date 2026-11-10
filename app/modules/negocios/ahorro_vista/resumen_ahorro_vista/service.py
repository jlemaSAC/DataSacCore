from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException
from pymongo.errors import PyMongoError

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.repositories.mongo_resumen_ahorro_vista_repository import (
    MongoResumenAhorroVistaRepository,
)
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.repositories.sql_resumen_ahorro_vista_repository import (
    CorteAhorroVistaNoDisponible,
    SqlResumenAhorroVistaRepository,
)
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.schemas import (
    AgenciaAhorroVista,
    AsesorAhorroVista,
    EstadoAhorroVista,
    FilaResumenAhorroVista,
    IndicadoresAhorroVista,
    InputResumenAhorroVista,
    MetricasAhorroVista,
    ProductoAhorroVista,
    ResumenAhorroVistaResponse,
    SaldoDiarioAhorroVista,
)


class ResumenAhorroVistaService:
    def __init__(
        self,
        sql_repository: SqlResumenAhorroVistaRepository,
        mongo_repository: MongoResumenAhorroVistaRepository,
    ) -> None:
        self.sql_repository = sql_repository
        self.mongo_repository = mongo_repository

    def obtener_resumen(
        self, body: InputResumenAhorroVista, auth: AuthContext
    ) -> ResumenAhorroVistaResponse:
        fecha_sistema = auth.usuario.fecha_sistema
        if isinstance(fecha_sistema, datetime):
            fecha_sistema = fecha_sistema.date()
        if body.fecha_fin > fecha_sistema:
            raise HTTPException(400, "La fecha de corte no puede superar la fecha del sistema.")
        mes_anterior = body.fecha_fin.replace(day=1) - timedelta(days=1)
        anio_anterior = date(body.fecha_fin.year - 1, 12, 31)
        cortes = {}
        filas_actuales: list[FilaResumenAhorroVista] = []
        cache = {}
        for nombre, fecha in (
            ("actual", body.fecha_fin),
            ("mes_anterior", mes_anterior),
            ("anio_anterior", anio_anterior),
        ):
            if fecha not in cache:
                filas = None
                corte = fecha
                if nombre != "actual":
                    try:
                        filas = self.mongo_repository.obtener_corte(fecha, es_programado=body.es_programado)
                    except PyMongoError:
                        # Mongo es una optimización del histórico; SQL conserva el origen.
                        filas = None
                if filas is None:
                    try:
                        corte, filas = self.sql_repository.obtener_corte(fecha, es_programado=body.es_programado)
                    except CorteAhorroVistaNoDisponible as exc:
                        if nombre == "actual":
                            raise HTTPException(409, str(exc)) from exc
                        corte, filas = None, []
                cache[fecha] = (corte, filas)
            corte, origen = cache[fecha]
            filas = [FilaResumenAhorroVista.model_validate(fila) for fila in origen]
            filas = [
                fila for fila in filas
                if not body.agencias or _etiqueta(fila.agencia) in body.agencias
            ]
            cortes[nombre] = (
                IndicadoresAhorroVista(fecha_corte=corte, **calcular_metricas(filas).model_dump())
                if corte is not None else None
            )
            if nombre == "actual":
                filas_actuales = filas
        detalles = {}
        for campo, modelo in (
            ("agencia", AgenciaAhorroVista),
            ("asesor", AsesorAhorroVista),
            ("estado", EstadoAhorroVista),
            ("producto_ahorro", ProductoAhorroVista),
        ):
            grupos: dict[str, list[FilaResumenAhorroVista]] = defaultdict(list)
            for fila in filas_actuales:
                grupos[_etiqueta(getattr(fila, campo))].append(fila)
            detalles[f"por_{campo}"] = [
                modelo(**{campo: etiqueta}, **calcular_metricas(grupo).model_dump())
                for etiqueta, grupo in sorted(grupos.items())
            ]
        # El corte final ya se obtuvo para indicadores y dimensiones. Reutilizarlo
        # evita otra lectura del saldo vivo y diferencias por movimientos en curso.
        historicos = self.sql_repository.obtener_saldos_diarios(
            body.fecha_inicio, body.fecha_fin - timedelta(days=1), body.agencias,
            es_programado=body.es_programado,
        )
        por_fecha = {
            (fila["fecha"].date() if isinstance(fila["fecha"], datetime) else fila["fecha"]):
                float(Decimal(str(fila["saldo"])).quantize(Decimal("0.01")))
            for fila in historicos
        }
        actual = cortes["actual"]
        if actual is not None and actual.fecha_corte == body.fecha_fin:
            por_fecha[body.fecha_fin] = actual.saldo
        saldo_diario = []
        fecha = body.fecha_inicio
        while fecha <= body.fecha_fin:
            saldo_diario.append(SaldoDiarioAhorroVista(fecha=fecha, saldo=por_fecha.get(fecha)))
            fecha += timedelta(days=1)
        return ResumenAhorroVistaResponse(
            fecha_inicio=body.fecha_inicio,
            fecha_fin=body.fecha_fin,
            fecha_mes_anterior=mes_anterior,
            fecha_anio_anterior=anio_anterior,
            consolidado=not body.agencias,
            agencias=body.agencias,
            saldo_diario=saldo_diario,
            **cortes,
            **detalles,
        )


def _etiqueta(valor: str) -> str:
    return valor.strip().upper() or "SIN DATOS"


def calcular_metricas(filas: list[FilaResumenAhorroVista]) -> MetricasAhorroVista:
    cuentas = sum(fila.numero_cuentas for fila in filas)
    saldo = sum((fila.saldo for fila in filas), Decimal(0))
    tasa = sum((fila.tasa_decimal * fila.numero_cuentas for fila in filas), Decimal(0))
    return MetricasAhorroVista(
        saldo=float(saldo.quantize(Decimal("0.01"))),
        numero_cuentas=cuentas,
        tasa_promedio=float((tasa / cuentas).quantize(Decimal("0.0001"))) if cuentas else None,
    )

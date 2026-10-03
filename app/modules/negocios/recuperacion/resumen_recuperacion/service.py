import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from time import perf_counter

from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.recuperacion.resumen_recuperacion.constants import TIPOS_COBRO
from app.modules.negocios.recuperacion.resumen_recuperacion.repositories.mongo_resumen_recuperacion_repository import (
    MongoResumenRecuperacionRepository,
)
from app.modules.negocios.recuperacion.resumen_recuperacion.schemas import (
    DiaResumenRecuperacion,
    InputResumenRecuperacion,
    RangoResumenRecuperacion,
    ResumenRecuperacionResponse,
)

logger = logging.getLogger("uvicorn.error")
CENTAVO = Decimal("0.01")


class ResumenRecuperacionService:
    def __init__(self, repository: MongoResumenRecuperacionRepository) -> None:
        self.repository = repository

    def obtener_resumen(
        self, body: InputResumenRecuperacion, auth_context: AuthContext
    ) -> ResumenRecuperacionResponse:
        fecha_sistema = auth_context.usuario.fecha_sistema
        hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        if body.fecha_fin > hoy:
            raise HTTPException(400, "fecha_fin no puede ser posterior a la fecha del sistema.")
        fin_mes_anterior = body.fecha_inicio.replace(day=1) - timedelta(days=1)
        anio_anterior = body.fecha_inicio.year - 1
        rangos = [
            (body.fecha_inicio, body.fecha_fin),
            (fin_mes_anterior.replace(day=1), fin_mes_anterior),
            (date(anio_anterior, 1, 1), date(anio_anterior, 12, 31)),
        ]
        inicio_consulta = perf_counter()
        try:
            filas = self.repository.obtener_diario(rangos, hoy, body.agencias)
            por_fecha: dict[date, dict[str, Decimal]] = {}
            for fila in filas:
                montos = por_fecha.setdefault(fila.fecha, _ceros())
                for tipo in TIPOS_COBRO:
                    montos[tipo] += fila.montos.get(tipo, Decimal(0))
            por_fecha = {
                fecha: {tipo: valor.quantize(CENTAVO, rounding=ROUND_HALF_UP) for tipo, valor in montos.items()}
                for fecha, montos in por_fecha.items()
            }
            resumenes = []
            for inicio, fin in rangos:
                montos = _ceros()
                for fecha, valores in por_fecha.items():
                    if inicio <= fecha <= fin:
                        for tipo in TIPOS_COBRO:
                            montos[tipo] += valores[tipo]
                resumenes.append(RangoResumenRecuperacion(
                    fecha_inicio=inicio, fecha_fin=fin, **_importes(montos)
                ))
            diario = []
            fecha = body.fecha_inicio
            while fecha <= body.fecha_fin:
                diario.append(DiaResumenRecuperacion(
                    fecha=fecha, **_importes(por_fecha.get(fecha, _ceros()))
                ))
                fecha += timedelta(days=1)
            logger.info("Resumen recuperación completado", extra={
                "duracion_ms": round((perf_counter() - inicio_consulta) * 1000, 2),
                "dias_agregados": len(filas),
            })
            return ResumenRecuperacionResponse(
                fecha_inicio=body.fecha_inicio, fecha_fin=body.fecha_fin,
                consolidado=not body.agencias, agencias=body.agencias,
                actual=resumenes[0], mes_anterior=resumenes[1], anio_anterior=resumenes[2],
                diario=diario,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error consultando resumen de recuperación")
            raise HTTPException(500, "No fue posible consultar el resumen de recuperación.") from exc


def _ceros() -> dict[str, Decimal]:
    return {tipo: Decimal(0) for tipo in TIPOS_COBRO}


def _importes(montos: dict[str, Decimal]) -> dict:
    return {
        "recuperacion_total": float(sum(montos.values(), Decimal(0))),
        "recuperacion_por_tipo": {tipo: float(monto) for tipo, monto in montos.items()},
    }

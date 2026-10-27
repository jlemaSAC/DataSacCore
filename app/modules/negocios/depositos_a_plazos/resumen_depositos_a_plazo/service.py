from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from app.modules.analytic.inversiones.schemas import ReporteInversionesFila
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.depositos_a_plazos.resumen_depositos_a_plazo.schemas import (
    AsesorResumenDepositos,
    CondicionResumenDepositos,
    DiaResumenDepositos,
    PeriodicidadResumenDepositos,
    ResumenDepositosAPlazoResponse,
)
from app.modules.negocios.inversiones.depositos_a_plazo.schemas import InputResumenActualDepositos
from app.modules.negocios.inversiones.depositos_a_plazo.service import (
    ResumenActualDepositosService,
    calcular_metricas_depositos,
)


class ResumenDepositosAPlazoService:
    def __init__(self, resumen_service: ResumenActualDepositosService) -> None:
        self.resumen_service = resumen_service

    def obtener_resumen(
        self, body: InputResumenActualDepositos, auth: AuthContext
    ) -> ResumenDepositosAPlazoResponse:
        resumen, filas = self.resumen_service.obtener_resumen_con_filas(body, auth)
        # El servicio compartido ya seleccionó una instantánea y filtró agencias.
        # Todas las vistas usan ese universo, no promedios de grupos ni otros cortes.
        dimensiones: dict[str, dict[str, list[ReporteInversionesFila]]] = {
            campo: defaultdict(list)
            for campo in ("asesor", "periodicidad_pago", "condicion")
        }
        por_fecha = defaultdict(list)
        for fila in filas:
            for campo, grupos in dimensiones.items():
                grupos[_etiqueta(getattr(fila, campo))].append(fila)
            if fila.fecha_creacion and body.fecha_inicio <= fila.fecha_creacion <= body.fecha_fin:
                por_fecha[fila.fecha_creacion].append(fila)

        fecha_corte = resumen.actual.fecha_corte if resumen.actual else body.fecha_fin
        detalles = {}
        for campo, salida, modelo in (
            ("asesor", "por_asesor", AsesorResumenDepositos),
            ("periodicidad_pago", "por_periodicidad", PeriodicidadResumenDepositos),
            ("condicion", "por_condicion", CondicionResumenDepositos),
        ):
            detalles[salida] = [
                modelo(**{
                    campo: etiqueta,
                    **calcular_metricas_depositos(
                        grupo, body.fecha_inicio, fecha_corte
                    ).model_dump(),
                })
                for etiqueta, grupo in sorted(dimensiones[campo].items())
            ]

        diario = []
        fecha = body.fecha_inicio
        while fecha <= body.fecha_fin:
            montos: dict[str, Decimal] = defaultdict(Decimal)
            operaciones = 0
            for fila in por_fecha.get(fecha, []):
                montos[_etiqueta(fila.condicion)] += Decimal(str(fila.saldo))
                operaciones += fila.operaciones
            diario.append(DiaResumenDepositos(
                fecha=fecha,
                monto_total=float(sum(montos.values(), Decimal(0)).quantize(Decimal("0.01"))),
                numero_operaciones=operaciones,
                monto_por_condicion={
                    condicion: float(monto.quantize(Decimal("0.01")))
                    for condicion, monto in sorted(montos.items())
                },
            ))
            fecha += timedelta(days=1)

        return ResumenDepositosAPlazoResponse(
            **resumen.model_dump(), **detalles, diario=diario
        )


def _etiqueta(valor: str) -> str:
    return valor.strip().upper() or "SIN DATOS"

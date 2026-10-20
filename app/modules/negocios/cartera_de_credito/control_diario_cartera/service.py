from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException

from .domain import ControlDiarioCarteraRepository, CorteAsesor
from .schemas import (
    ControlDiarioCarteraRequest,
    ControlDiarioCarteraResponse,
    DiaControlCartera,
    FilaControlDiarioCartera,
    VariacionCarteraValores,
)


class ControlDiarioCarteraService:
    def __init__(self, repository: ControlDiarioCarteraRepository) -> None:
        self.repository = repository

    def obtener(
        self,
        request: ControlDiarioCarteraRequest,
        *,
        fecha_limite: date,
    ) -> ControlDiarioCarteraResponse:
        inicio, fin = request.fecha_inicio, request.fecha_fin
        if inicio > fin:
            raise HTTPException(400, "La fecha de inicio no puede ser posterior a la fecha de fin.")
        if fin > fecha_limite:
            raise HTTPException(400, "La fecha de fin no puede ser posterior a la fecha del sistema.")
        comparaciones = []
        for i in range((fin - inicio).days + 1):
            fecha = inicio + timedelta(days=i)
            cierre_anterior = fecha.replace(day=1) - timedelta(days=1)
            if request.tipo_variacion == 'cierre_mes_anterior':
                anterior = cierre_anterior
            elif request.tipo_variacion == 'mismo_dia_mes_anterior':
                anterior = cierre_anterior.replace(day=min(fecha.day, cierre_anterior.day))
            else:
                anterior = fecha - timedelta(days=1)
            comparaciones.append((fecha, anterior))
        cortes = self.repository.obtener_cortes(
            desde=min(anterior for _, anterior in comparaciones),
            hasta=fin,
            agencia=request.agencia,
            filtrar_diferidos=request.filtrar_diferidos,
        )
        dias = [
            DiaControlCartera(
                fecha=fecha,
                fecha_anterior=anterior,
                disponible=fecha in cortes.fechas and anterior in cortes.fechas,
            )
            for fecha, anterior in comparaciones
        ]
        # La última identificación de cada asesor/agencia mantiene estable el filtro de cargos.
        por_asesor: dict[tuple[str, str], dict[date, CorteAsesor]] = {}
        fechas_relevantes = {
            fecha
            for dia in dias
            for fecha in (dia.fecha, dia.fecha_anterior)
        }
        for corte in cortes.asesores:
            if corte.fecha in fechas_relevantes:
                por_asesor.setdefault((corte.codigo_asesor, corte.agencia), {})[corte.fecha] = corte
        filas = []
        ordenados = sorted(por_asesor.items(), key=lambda item: (item[0][1], item[0][0]))
        for (codigo, agencia), valores in ordenados:
            ultimo = valores[max(valores)]
            filas.append(FilaControlDiarioCartera(
                codigo_asesor=codigo,
                nombre_asesor=ultimo.nombre_asesor,
                cargo=ultimo.cargo,
                agencia=agencia,
                variaciones=[
                    _variacion(valores.get(dia.fecha), valores.get(dia.fecha_anterior))
                    if dia.disponible else None
                    for dia in dias
                ],
            ))
        return ControlDiarioCarteraResponse(
            fecha_inicio=inicio,
            fecha_fin=fin,
            agencia=request.agencia,
            filtrar_diferidos=request.filtrar_diferidos,
            tipo_variacion=request.tipo_variacion,
            dias=dias,
            filas=filas,
        )


def _variacion(
    actual: CorteAsesor | None, anterior: CorteAsesor | None,
) -> VariacionCarteraValores:
    def delta(campo: str) -> float:
        return float(round(
            getattr(actual, campo, Decimal(0)) - getattr(anterior, campo, Decimal(0)),
            2,
        ))
    return VariacionCarteraValores(
        saldo_capital=delta("saldo_capital"),
        cartera_improductiva=delta("cartera_improductiva"),
        provisiones=delta("provisiones"),
    )

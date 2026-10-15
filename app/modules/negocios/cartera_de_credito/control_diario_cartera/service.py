from calendar import monthrange
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
        inicio = date.fromisoformat(f"{request.mes}-01")
        if inicio > fecha_limite:
            raise HTTPException(400, "El mes no puede ser posterior a la fecha del sistema.")
        fin = inicio.replace(day=monthrange(inicio.year, inicio.month)[1])
        cortes = self.repository.obtener_cortes(
            desde=inicio - timedelta(days=1),
            hasta=min(fin, fecha_limite),
            agencia=request.agencia,
            filtrar_diferidos=request.filtrar_diferidos,
        )
        dias = []
        for i in range(fin.day):
            fecha = inicio + timedelta(days=i)
            anterior = fecha - timedelta(days=1)
            dias.append(DiaControlCartera(
                fecha=fecha,
                fecha_anterior=anterior,
                disponible=fecha in cortes.fechas and anterior in cortes.fechas,
            ))
        # La última identificación de cada asesor/agencia mantiene estable el filtro de cargos.
        por_asesor: dict[tuple[str, str], dict[date, CorteAsesor]] = {}
        for corte in cortes.asesores:
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
            mes=request.mes,
            agencia=request.agencia,
            filtrar_diferidos=request.filtrar_diferidos,
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

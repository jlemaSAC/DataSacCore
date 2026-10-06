from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.colocacion.diaria_asesores.schemas import (
    ColocacionAsesorComparativo,
    ColocacionDiariaAsesoresResponse,
    ColocacionIndicadores,
    ColocacionResumenComparativo,
)


class ColocacionDiariaAsesoresService:
    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def obtener(
        self,
        *,
        id_agencia: int,
        auth_context: AuthContext,
    ) -> ColocacionDiariaAsesoresResponse:
        fecha_sistema = auth_context.usuario.fecha_sistema
        fecha = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        fecha_ayer = fecha - timedelta(days=1)
        resultado = self.repository.obtener_colocaciones(id_agencia=id_agencia, fecha=fecha)
        if resultado is None:
            raise HTTPException(status_code=404, detail="La agencia no existe.")

        asesores: list[ColocacionAsesorComparativo] = []
        total_operaciones_hoy = 0
        total_monto_hoy = 0.0
        total_operaciones_ayer = 0
        total_monto_ayer = 0.0
        for fila in resultado.asesores:
            operaciones_hoy = fila.operaciones_hoy
            monto_hoy = round(fila.monto_colocado_hoy, 2)
            operaciones_ayer = fila.operaciones_ayer
            monto_ayer = round(fila.monto_colocado_ayer, 2)
            total_operaciones_hoy += operaciones_hoy
            total_monto_hoy += monto_hoy
            total_operaciones_ayer += operaciones_ayer
            total_monto_ayer += monto_ayer
            asesores.append(
                ColocacionAsesorComparativo(
                    codigo_usuario=fila.codigo_usuario,
                    asesor=fila.asesor,
                    hoy=ColocacionIndicadores(
                        operaciones=operaciones_hoy,
                        monto_colocado=monto_hoy,
                    ),
                    ayer=ColocacionIndicadores(
                        operaciones=operaciones_ayer,
                        monto_colocado=monto_ayer,
                    ),
                    cambio=ColocacionIndicadores(
                        operaciones=operaciones_hoy - operaciones_ayer,
                        monto_colocado=round(monto_hoy - monto_ayer, 2),
                    ),
                )
            )

        monto_total_hoy = round(total_monto_hoy, 2)
        monto_total_ayer = round(total_monto_ayer, 2)
        return ColocacionDiariaAsesoresResponse(
            fecha=fecha,
            fecha_ayer=fecha_ayer,
            id_agencia=resultado.id_agencia,
            agencia=resultado.agencia,
            resumen=ColocacionResumenComparativo(
                hoy=ColocacionIndicadores(
                    operaciones=total_operaciones_hoy,
                    monto_colocado=monto_total_hoy,
                ),
                ayer=ColocacionIndicadores(
                    operaciones=total_operaciones_ayer,
                    monto_colocado=monto_total_ayer,
                ),
                cambio=ColocacionIndicadores(
                    operaciones=total_operaciones_hoy - total_operaciones_ayer,
                    monto_colocado=round(monto_total_hoy - monto_total_ayer, 2),
                ),
            ),
            asesores=asesores,
        )

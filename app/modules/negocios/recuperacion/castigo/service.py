import logging
from datetime import date, datetime

from fastapi import HTTPException

from app.modules.negocios.recuperacion.castigo.repositories.mongo_castigo_repository import (
    MongoCastigoRepository,
)
from app.modules.negocios.recuperacion.castigo.schemas import (
    DepositoCastigoDiarioOut,
    DepositosCastigoCatalogosOut,
    DepositosCastigoResponse,
    InputDepositosCastigo,
)
from app.modules.auth.schemas import AuthContext


logger = logging.getLogger("uvicorn.error")
MAX_MESES_RANGO = 60


class CastigoService:
    def __init__(self, mongo_repository: MongoCastigoRepository) -> None:
        self.mongo_repository = mongo_repository

    def obtener_depositos_diarios(
        self,
        input_data: InputDepositosCastigo,
        auth_context: AuthContext,
    ) -> DepositosCastigoResponse:
        fecha_sistema = auth_context.usuario.fecha_sistema
        fecha_actual = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        self._validar_rango(input_data, fecha_actual)

        try:
            resultado = self.mongo_repository.obtener_depositos_diarios(
                fecha_desde=input_data.fecha_desde,
                fecha_hasta=input_data.fecha_hasta,
                fecha_actual=fecha_actual,
                agencias=input_data.agencias,
                asesores=input_data.asesores,
                cargos=input_data.cargos,
            )
            depositos: list[DepositoCastigoDiarioOut] = []
            for fila in resultado.get("depositos", []):
                clave = fila.get("_id") or {}
                depositos.append(
                    DepositoCastigoDiarioOut(
                        numero_prestamo=str(clave.get("numero_prestamo") or ""),
                        fecha=datetime.strptime(str(clave.get("fecha")), "%Y%m%d").date(),
                        estado_inicio=str(clave.get("estado_prestamo_inicio") or ""),
                        estado_fin=str(clave.get("estado_prestamo_fin") or ""),
                        tipo_transaccion=str(clave.get("tipo_transaccion") or ""),
                        agencia=str(clave.get("agencia") or ""),
                        codigo_asesor=str(clave.get("codigo_asesor") or ""),
                        asesor=str(clave.get("asesor") or ""),
                        cargo_asesor=str(clave.get("cargo_asesor") or ""),
                        total_depositado=float(fila.get("total_recuperado") or 0),
                    )
                )

            total_depositado = sum(item.total_depositado for item in depositos)
            catalogos_raw = resultado.get("catalogos", {})
            catalogos = DepositosCastigoCatalogosOut(
                agencias=catalogos_raw.get("agencias", []),
                asesores=catalogos_raw.get("asesores", []),
                cargos=catalogos_raw.get("cargos", []),
            )
            logger.debug(
                "castigo_depositos_diarios_consulta_completada",
                extra={
                    "fecha_desde": input_data.fecha_desde.isoformat(),
                    "fecha_hasta": input_data.fecha_hasta.isoformat(),
                    "depositos": len(depositos),
                    "total_depositado": total_depositado,
                },
            )
            return DepositosCastigoResponse(
                fecha_desde=input_data.fecha_desde,
                fecha_hasta=input_data.fecha_hasta,
                depositos=depositos,
                total_depositado=total_depositado,
                catalogos=catalogos,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error consultando depósitos diarios de préstamos castigados")
            raise HTTPException(
                status_code=500,
                detail=f"Error consultando depósitos diarios de castigos: {exc}",
            ) from exc

    @staticmethod
    def _validar_rango(
        input_data: InputDepositosCastigo,
        fecha_actual: date,
    ) -> None:
        if input_data.fecha_hasta > fecha_actual:
            raise HTTPException(
                status_code=400,
                detail="fecha_hasta no puede ser posterior a la fecha del sistema.",
            )
        meses = (
            (input_data.fecha_hasta.year - input_data.fecha_desde.year) * 12
            + input_data.fecha_hasta.month
            - input_data.fecha_desde.month
            + 1
        )
        if meses > MAX_MESES_RANGO:
            raise HTTPException(
                status_code=400,
                detail=f"El rango no puede superar {MAX_MESES_RANGO} meses.",
            )

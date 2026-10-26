from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)
from app.modules.negocios.depositos_a_plazos.control_diario_cancelacion.repositories.sql_control_diario_cancelacion_repository import (
    SqlControlDiarioCancelacionRepository,
)
from app.modules.negocios.depositos_a_plazos.control_diario_cancelacion.schemas import (
    CancelacionDia,
    ControlDiarioCancelacionFila,
    ControlDiarioCancelacionRequest,
    ControlDiarioCancelacionResponse,
    DetalleControlCancelacionFila,
    DetalleControlCancelacionRequest,
    DetalleControlCancelacionResponse,
)


class ControlDiarioCancelacionService:
    def __init__(
        self, repository: SqlControlDiarioCancelacionRepository,
        catalogo: SqlSituacionCrediticiaAsesoresRepository,
    ) -> None:
        self.repository = repository
        self.catalogo = catalogo

    def obtener(
        self, body: ControlDiarioCancelacionRequest, auth: AuthContext
    ) -> ControlDiarioCancelacionResponse:
        fecha_sistema = self._validar_consulta(body, auth)
        corte = self.repository.obtener_diario(**body.model_dump(), fecha_sistema=fecha_sistema)
        if corte is None:
            raise HTTPException(404, f"No existe un corte de depósitos disponible para {body.fecha_fin}.")

        dias = [
            body.fecha_inicio + timedelta(days=i)
            for i in range((body.fecha_fin - body.fecha_inicio).days + 1)
        ]
        return ControlDiarioCancelacionResponse(
            **body.model_dump(), fecha_corte=corte.fecha, dias=dias,
            filas=self._agrupar_filas(corte.filas, dias),
        )

    @staticmethod
    def _agrupar_filas(datos: list[dict[str, Any]], dias: list[date]) -> list[ControlDiarioCancelacionFila]:
        indices = {dia: indice for indice, dia in enumerate(dias)}
        grupos: dict[tuple[str, int], ControlDiarioCancelacionFila] = {}
        montos: dict[tuple[str, int], list[dict[str, Decimal]]] = {}
        for dato in datos:
            fecha = dato["fecha"]
            if isinstance(fecha, datetime):
                fecha = fecha.date()
            if fecha not in indices:
                continue
            clave = (str(dato["codigo"]), int(dato["IDAGENCIA"]))
            if clave not in grupos:
                grupos[clave] = ControlDiarioCancelacionFila(
                    codigo_usuario=clave[0], id_agencia=clave[1],
                    nombre_captador=dato["nombre"].strip(), cargo=dato["cargo"].strip().upper(),
                    agencia=dato["agencia"].strip().upper(), valores=[],
                )
                montos[clave] = [{"nuevo": Decimal(0), "renovado": Decimal(0)} for _ in dias]
            valores = montos[clave][indices[fecha]]
            condicion = dato["condicion"].strip().lower()
            valores[condicion] += Decimal(str(dato["monto"]))
        for clave, fila in grupos.items():
            fila.valores = [
                CancelacionDia(**{
                    condicion: float(monto.quantize(Decimal("0.01")))
                    for condicion, monto in dia.items()
                })
                for dia in montos[clave]
            ]
        return sorted(grupos.values(), key=lambda f: (f.agencia, f.nombre_captador, f.codigo_usuario))

    def obtener_detalle(
        self, body: DetalleControlCancelacionRequest, auth: AuthContext
    ) -> DetalleControlCancelacionResponse:
        fecha_sistema = self._validar_consulta(body, auth)
        corte = self.repository.obtener_detalle(**body.model_dump(), fecha_sistema=fecha_sistema)
        if corte is None:
            raise HTTPException(404, f"No existe un cierre completo disponible para {body.fecha_fin}.")
        return DetalleControlCancelacionResponse(
            **body.model_dump(), fecha_corte=corte.fecha,
            total_registros=len(corte.filas),
            total_monto=float(sum((Decimal(str(f["monto"])) for f in corte.filas), Decimal(0)).quantize(Decimal("0.01"))),
            total_interes=float(sum((Decimal(str(f["interes_total"])) for f in corte.filas), Decimal(0)).quantize(Decimal("0.01"))),
            items=[DetalleControlCancelacionFila.model_validate({
                **fila, "numero_cliente": str(fila["numero_cliente"]),
            }) for fila in corte.filas],
        )

    def _validar_consulta(self, body: ControlDiarioCancelacionRequest, auth: AuthContext) -> date:
        fecha_sistema = auth.usuario.fecha_sistema
        if isinstance(fecha_sistema, datetime):
            fecha_sistema = fecha_sistema.date()
        if body.fecha_fin > fecha_sistema:
            raise HTTPException(400, "fecha_fin no puede superar la fecha del sistema.")
        if body.id_agencia and not self.catalogo.obtener_nombre_agencia(body.id_agencia):
            raise HTTPException(404, "La agencia no existe.")
        return fecha_sistema

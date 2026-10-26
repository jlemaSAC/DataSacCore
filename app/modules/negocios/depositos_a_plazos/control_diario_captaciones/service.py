from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.repositories.sql_control_diario_captaciones_repository import (
    SqlControlDiarioCaptacionesRepository,
)
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.schemas import (
    CaptacionesDia,
    ControlDiarioCaptacionesFila,
    ControlDiarioCaptacionesRequest,
    ControlDiarioCaptacionesResponse,
    DetalleControlCaptacionesFila,
    DetalleControlCaptacionesRequest,
    DetalleControlCaptacionesResponse,
)


class ControlDiarioCaptacionesService:
    def __init__(
        self, repository: SqlControlDiarioCaptacionesRepository,
        catalogo: SqlSituacionCrediticiaAsesoresRepository,
    ) -> None:
        self.repository = repository
        self.catalogo = catalogo

    def obtener(
        self, body: ControlDiarioCaptacionesRequest, auth: AuthContext
    ) -> ControlDiarioCaptacionesResponse:
        fecha_sistema = self._validar_consulta(body, auth)
        corte = self.repository.obtener_diario(**body.model_dump(), fecha_sistema=fecha_sistema)
        if corte is None:
            raise HTTPException(404, f"No existe un corte de depósitos disponible para {body.fecha_fin}.")

        dias = [
            body.fecha_inicio + timedelta(days=i)
            for i in range((body.fecha_fin - body.fecha_inicio).days + 1)
        ]
        grupos: dict[tuple[str, int], ControlDiarioCaptacionesFila] = {}
        montos: dict[tuple[str, int], list[dict[str, Decimal]]] = {}
        for dato in corte.filas:
            fecha = dato["fecha"]
            if isinstance(fecha, datetime):
                fecha = fecha.date()
            if not body.fecha_inicio <= fecha <= body.fecha_fin:
                continue
            clave = (str(dato["codigo"]), int(dato["IDAGENCIA"]))
            if clave not in grupos:
                grupos[clave] = ControlDiarioCaptacionesFila(
                    codigo_usuario=clave[0], id_agencia=clave[1],
                    nombre_captador=dato["nombre"].strip(), cargo=dato["cargo"].strip().upper(),
                    agencia=dato["agencia"].strip().upper(), valores=[],
                )
                montos[clave] = [{"nuevo": Decimal(0), "renovado": Decimal(0)} for _ in dias]
            valores = montos[clave][(fecha - body.fecha_inicio).days]
            condicion = dato["condicion"].strip().lower()
            valores[condicion] += Decimal(str(dato["monto"]))
        for clave, fila in grupos.items():
            fila.valores = [
                CaptacionesDia(**{
                    condicion: float(monto.quantize(Decimal("0.01")))
                    for condicion, monto in dia.items()
                })
                for dia in montos[clave]
            ]
        return ControlDiarioCaptacionesResponse(
            **body.model_dump(), fecha_corte=corte.fecha, dias=dias,
            filas=sorted(grupos.values(), key=lambda f: (f.agencia, f.nombre_captador, f.codigo_usuario)),
        )

    def obtener_detalle(
        self, body: DetalleControlCaptacionesRequest, auth: AuthContext
    ) -> DetalleControlCaptacionesResponse:
        fecha_sistema = self._validar_consulta(body, auth)
        corte = self.repository.obtener_detalle(**body.model_dump(), fecha_sistema=fecha_sistema)
        if corte is None:
            raise HTTPException(404, f"No existe un cierre completo disponible para {body.fecha_fin}.")
        return DetalleControlCaptacionesResponse(
            **body.model_dump(), fecha_corte=corte.fecha,
            total_registros=len(corte.filas),
            total_monto=float(sum((Decimal(str(f["monto"])) for f in corte.filas), Decimal(0)).quantize(Decimal("0.01"))),
            total_interes=float(sum((Decimal(str(f["interes_total"])) for f in corte.filas), Decimal(0)).quantize(Decimal("0.01"))),
            items=[DetalleControlCaptacionesFila.model_validate({
                **fila, "numero_cliente": str(fila["numero_cliente"]),
            }) for fila in corte.filas],
        )

    def _validar_consulta(self, body: ControlDiarioCaptacionesRequest, auth: AuthContext) -> date:
        fecha_sistema = auth.usuario.fecha_sistema
        if isinstance(fecha_sistema, datetime):
            fecha_sistema = fecha_sistema.date()
        if body.fecha_fin > fecha_sistema:
            raise HTTPException(400, "fecha_fin no puede superar la fecha del sistema.")
        if body.id_agencia and not self.catalogo.obtener_nombre_agencia(body.id_agencia):
            raise HTTPException(404, "La agencia no existe.")
        return fecha_sistema

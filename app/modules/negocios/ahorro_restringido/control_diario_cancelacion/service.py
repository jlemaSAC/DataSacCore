from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.ahorro_restringido.control_diario_cancelacion.repositories.sql_cancelacion_restringidos_repository import (
    CorteCancelacionRestringidos,
    SqlCancelacionRestringidosRepository,
)
from app.modules.negocios.ahorro_restringido.control_diario_cancelacion.schemas import (
    CancelacionRestringidosDia,
    CancelacionRestringidosFila,
    ControlCancelacionRestringidosRequest,
    ControlCancelacionRestringidosResponse,
    DetalleCancelacionRestringidosItem,
    DetalleCancelacionRestringidosRequest,
    DetalleCancelacionRestringidosResponse,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)


def _moneda(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


class ControlCancelacionRestringidosService:
    def __init__(
        self, repository: SqlCancelacionRestringidosRepository,
        catalogo: SqlSituacionCrediticiaAsesoresRepository,
    ) -> None:
        self.repository = repository
        self.catalogo = catalogo

    def _consultar(
        self, body: ControlCancelacionRestringidosRequest, auth: AuthContext,
    ) -> CorteCancelacionRestringidos:
        fecha_sistema = auth.usuario.fecha_sistema
        if isinstance(fecha_sistema, datetime):
            fecha_sistema = fecha_sistema.date()
        if body.fecha_fin > fecha_sistema:
            raise HTTPException(400, "fecha_fin no puede superar la fecha del sistema.")
        if body.id_agencia and not self.catalogo.obtener_nombre_agencia(body.id_agencia):
            raise HTTPException(404, "La agencia no existe.")
        corte = self.repository.obtener_corte(
            fecha_inicio=body.fecha_inicio, fecha_fin=body.fecha_fin,
            id_agencia=body.id_agencia, fecha_sistema=fecha_sistema,
        )
        if corte is None:
            raise HTTPException(404, f"No existe un cierre de ahorros disponible para {body.fecha_fin}.")
        return corte

    def obtener(
        self, body: ControlCancelacionRestringidosRequest, auth: AuthContext,
    ) -> ControlCancelacionRestringidosResponse:
        corte = self._consultar(body, auth)
        dias = [body.fecha_inicio + timedelta(days=i)
                for i in range((body.fecha_fin - body.fecha_inicio).days + 1)]
        grupos = defaultdict(list)
        for fila in corte.filas:
            grupos[(fila["codigo_usuario"], fila["id_agencia"], fila["codigo_producto"])].append(fila)
        filas = []
        for grupo in grupos.values():
            por_dia = defaultdict(list)
            for fila in grupo:
                fecha = fila["fecha_cancelacion"]
                por_dia[fecha.date() if isinstance(fecha, datetime) else fecha].append(fila)
            filas.append(CancelacionRestringidosFila(
                **{campo: grupo[0][campo] for campo in (
                    "codigo_usuario", "nombre_asesor", "cargo", "id_agencia", "agencia",
                    "codigo_producto", "producto_ahorro",
                )},
                valores=[CancelacionRestringidosDia(
                    monto=_moneda(sum((Decimal(str(f["monto"])) for f in por_dia[dia]), Decimal(0))),
                    cuentas=len(por_dia[dia]),
                ) for dia in dias],
            ))
        return ControlCancelacionRestringidosResponse(
            **body.model_dump(), fecha_corte=corte.fecha, dias=dias, filas=filas,
        )

    def obtener_detalle(
        self, body: DetalleCancelacionRestringidosRequest, auth: AuthContext,
    ) -> DetalleCancelacionRestringidosResponse:
        corte = self._consultar(body, auth)
        filas = [fila for fila in corte.filas
                 if (body.fecha is None or str(fila["fecha_cancelacion"])[:10] == body.fecha.isoformat())
                 and (body.codigo_usuario is None or fila["codigo_usuario"] == body.codigo_usuario)
                 and (not body.cargos or fila["cargo"].strip().upper() in body.cargos)
                 and (not body.productos or fila["codigo_producto"] in body.productos)]
        return DetalleCancelacionRestringidosResponse(
            **body.model_dump(), fecha_corte=corte.fecha, total_registros=len(filas),
            total_monto=_moneda(sum((Decimal(str(f["monto"])) for f in filas), Decimal(0))),
            items=[DetalleCancelacionRestringidosItem.model_validate(fila) for fila in filas],
        )

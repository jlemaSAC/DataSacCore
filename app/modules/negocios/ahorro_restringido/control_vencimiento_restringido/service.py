from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)
from app.modules.negocios.ahorro_restringido.control_vencimiento_restringido.repositories.sql_control_vencimiento_restringido_repository import (
    SqlControlVencimientoRestringidoRepository,
)
from app.modules.negocios.ahorro_restringido.control_vencimiento_restringido.schemas import (
    ControlVencimientoRestringidoFila,
    ControlVencimientoRestringidoRequest,
    ControlVencimientoRestringidoResponse,
    DetalleControlVencimientoRestringidoFila,
    DetalleControlVencimientoRestringidoRequest,
    DetalleControlVencimientoRestringidoResponse,
)


class ControlVencimientoRestringidoService:
    def __init__(
        self, repository: SqlControlVencimientoRestringidoRepository,
        catalogo: SqlSituacionCrediticiaAsesoresRepository,
    ) -> None:
        self.repository = repository
        self.catalogo = catalogo

    def obtener(self, body: ControlVencimientoRestringidoRequest, auth: AuthContext) -> ControlVencimientoRestringidoResponse:
        if body.id_agencia and not self.catalogo.obtener_nombre_agencia(body.id_agencia):
            raise HTTPException(404, "La agencia no existe.")
        datos = self.repository.obtener_saldos(
            fecha_inicio=body.fecha_inicio, fecha_fin=body.fecha_fin, id_agencia=body.id_agencia,
        )
        filas = [
            ControlVencimientoRestringidoFila(
                clave=f"{fila['codigo']}::{fila['IDAGENCIA']}::{fila['codigo_producto']}",
                codigo_usuario=fila["codigo"], nombre_asesor=fila["nombre"],
                codigo_producto=fila["codigo_producto"], producto_ahorro=fila["producto_ahorro"],
                cargo=fila["cargo"], id_agencia=fila["IDAGENCIA"], agencia=fila["agencia"],
                saldo=float(Decimal(str(fila["saldo"])).quantize(Decimal("0.01"))),
            )
            for fila in datos
        ]
        fecha_sistema = auth.usuario.fecha_sistema
        if isinstance(fecha_sistema, datetime):
            fecha_sistema = fecha_sistema.date()
        return ControlVencimientoRestringidoResponse(
            fecha_inicio=body.fecha_inicio, fecha_fin=body.fecha_fin,
            id_agencia=body.id_agencia, fecha_sistema=fecha_sistema,
            saldo_total=float(sum((Decimal(str(f["saldo"])) for f in datos), Decimal("0.00"))),
            filas=filas,
            agencias_gerentes_oficina=self.catalogo.obtener_gerentes_oficina(
                sorted({fila.agencia for fila in filas}),
            ),
        )

    def obtener_detalle(self, body: DetalleControlVencimientoRestringidoRequest) -> DetalleControlVencimientoRestringidoResponse:
        if body.id_agencia and not self.catalogo.obtener_nombre_agencia(body.id_agencia):
            raise HTTPException(404, "La agencia no existe.")
        resultado = self.repository.obtener_detalle(**body.model_dump())
        return DetalleControlVencimientoRestringidoResponse(
            **body.model_dump(exclude={"pagina", "tamano_pagina", "sin_paginacion"}),
            pagina=None if body.sin_paginacion else body.pagina,
            tamano_pagina=None if body.sin_paginacion else body.tamano_pagina,
            total_registros=resultado.total_registros,
            total_saldo=float(resultado.total_saldo),
            items=[DetalleControlVencimientoRestringidoFila.model_validate({
                **fila, "numero_cliente": str(fila["numero_cliente"]),
            }) for fila in resultado.items],
        )

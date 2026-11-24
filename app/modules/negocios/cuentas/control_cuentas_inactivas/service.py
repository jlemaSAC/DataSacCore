from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)

from ..resumen import fecha_de_sistema, ids_agencia, resumir_por_agencia
from ..schemas import ResumenOficialTipoCuenta
from .repositories.sql_control_cuentas_inactivas_repository import SqlControlCuentasInactivasRepository
from .schemas import (
    ConsultaCuentasInactivas,
    ConsultaCuentasInactivasResponse,
    CuentaInactivaDetalle,
    DetalleCuentasInactivasRequest,
    DetalleCuentasInactivasResponse,
)


class ControlCuentasInactivasService:
    def __init__(
        self, repositorio: SqlControlCuentasInactivasRepository,
        catalogo: SqlSituacionCrediticiaAsesoresRepository,
    ) -> None:
        self.repositorio = repositorio
        self.catalogo = catalogo

    def consultar(
        self, body: ConsultaCuentasInactivas, auth: AuthContext,
    ) -> ConsultaCuentasInactivasResponse:
        fecha_sistema = fecha_de_sistema(auth)
        desglose = [
            ResumenOficialTipoCuenta.model_validate(fila)
            for fila in self.repositorio.obtener_desglose(
                ids_agencia(body), fecha_sistema=fecha_sistema,
                inactividad=body.inactividad, saldo=body.saldo,
            )
        ]
        resumen, total = resumir_por_agencia(desglose, self.catalogo)

        return ConsultaCuentasInactivasResponse(
            id_agencia=body.id_agencia, fecha_sistema=fecha_sistema,
            resumen=resumen, desglose=desglose, total=total,
        )

    def detalle(
        self, body: DetalleCuentasInactivasRequest, auth: AuthContext,
    ) -> DetalleCuentasInactivasResponse:
        fecha_sistema = fecha_de_sistema(auth)
        total, filas = self.repositorio.obtener_detalle(
            **body.model_dump(exclude={"id_agencia", "ids_agencia"}),
            ids_agencia=ids_agencia(body), fecha_sistema=fecha_sistema,
        )
        return DetalleCuentasInactivasResponse(
            fecha_sistema=fecha_sistema,
            pagina=None if body.sin_paginacion else body.pagina,
            tamano_pagina=None if body.sin_paginacion else body.tamano_pagina,
            total_registros=total,
            filas=[CuentaInactivaDetalle.model_validate(fila) for fila in filas],
        )

from datetime import date, datetime

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)

from .repositories.sql_control_cuentas_inactivas_repository import SqlControlCuentasInactivasRepository
from .schemas import (
    ConsultaCuentasInactivas,
    ConsultaCuentasInactivasResponse,
    CuentaInactivaDetalle,
    DetalleCuentasInactivasRequest,
    DetalleCuentasInactivasResponse,
    IndicadoresCuentas,
    ResumenAgencia,
    ResumenOficialTipoCuenta,
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
        fecha_sistema = self._fecha_sistema(auth)
        desglose = [
            ResumenOficialTipoCuenta.model_validate(fila)
            for fila in self.repositorio.obtener_desglose(
                self._ids_agencia(body), fecha_sistema=fecha_sistema,
                inactividad=body.inactividad, saldo=body.saldo,
            )
        ]
        responsables = {
            fila["IdAgencia"]: fila
            for fila in self.catalogo.obtener_gerentes_oficina({fila.agencia for fila in desglose})
        }
        resumen: dict[int, ResumenAgencia] = {}
        total: IndicadoresCuentas | None = None
        for fila in desglose:
            clave = fila.id_agencia
            if clave not in resumen:
                responsable = responsables.get(fila.id_agencia, {})
                resumen[clave] = ResumenAgencia.model_validate({
                    **fila.model_dump(),
                    "cargo_jefe_agencia": responsable.get("Cargo"),
                    "nombre_jefe_agencia": responsable.get("GerenteOficina"),
                })
            else:
                self._acumular(resumen[clave], fila)
            if total is None:
                total = IndicadoresCuentas.model_validate(fila.model_dump())
            else:
                self._acumular(total, fila)

        return ConsultaCuentasInactivasResponse(
            id_agencia=body.id_agencia, fecha_sistema=fecha_sistema,
            resumen=list(resumen.values()), desglose=desglose, total=total,
        )

    def detalle(
        self, body: DetalleCuentasInactivasRequest, auth: AuthContext,
    ) -> DetalleCuentasInactivasResponse:
        fecha_sistema = self._fecha_sistema(auth)
        total, filas = self.repositorio.obtener_detalle(
            **body.model_dump(exclude={"id_agencia", "ids_agencia"}),
            ids_agencia=self._ids_agencia(body), fecha_sistema=fecha_sistema,
        )
        return DetalleCuentasInactivasResponse(
            fecha_sistema=fecha_sistema,
            pagina=None if body.sin_paginacion else body.pagina,
            tamano_pagina=None if body.sin_paginacion else body.tamano_pagina,
            total_registros=total,
            filas=[CuentaInactivaDetalle.model_validate(fila) for fila in filas],
        )

    @staticmethod
    def _ids_agencia(body: ConsultaCuentasInactivas) -> list[int]:
        return sorted(set(body.ids_agencia)) if body.id_agencia == 0 else [body.id_agencia]

    @staticmethod
    def _acumular(acumulado: IndicadoresCuentas, fila: IndicadoresCuentas) -> None:
        acumulado.cantidad_cuentas += fila.cantidad_cuentas
        acumulado.valor_disponible += fila.valor_disponible
        acumulado.valor_total += fila.valor_total

    @staticmethod
    def _fecha_sistema(auth: AuthContext) -> date:
        fecha = auth.usuario.fecha_sistema
        return fecha.date() if isinstance(fecha, datetime) else fecha

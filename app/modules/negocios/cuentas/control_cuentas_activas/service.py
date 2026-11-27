from fastapi import HTTPException

from app.modules.auth.repositories.sql_auth_repository import SqlAuthRepository
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)

from ..resumen import fecha_de_sistema, ids_agencia
from .repositories.sql_control_cuentas_activas_repository import SqlControlCuentasActivasRepository
from .schemas import (
    ConsultaCuentasReactivadas,
    ConsultaCuentasReactivadasResponse,
    DesgloseReactivaciones,
    DetalleCuentasReactivadasRequest,
    DetalleCuentasReactivadasResponse,
    IndicadoresReactivaciones,
    ReactivacionDetalle,
    ResumenReactivaciones,
)


class ControlCuentasActivasService:
    def __init__(
        self, repositorio: SqlControlCuentasActivasRepository, oficinas: SqlAuthRepository,
        catalogo: SqlSituacionCrediticiaAsesoresRepository,
    ) -> None:
        self.repositorio = repositorio
        self.oficinas = oficinas
        self.catalogo = catalogo

    def consultar(
        self, body: ConsultaCuentasReactivadas, auth: AuthContext,
    ) -> ConsultaCuentasReactivadasResponse:
        agencias = self._validar_consulta(body, auth)
        desglose = [
            DesgloseReactivaciones.model_validate(fila)
            for fila in self.repositorio.obtener_resumen(agencias, body.fecha_inicio, body.fecha_fin)
        ]
        responsables = {
            fila["IdAgencia"]: fila
            for fila in self.catalogo.obtener_gerentes_oficina({fila.agencia for fila in desglose})
        }
        por_agencia_tipo: dict[tuple[int, str], ResumenReactivaciones] = {}
        total = IndicadoresReactivaciones(cantidad_cuentas=0, cantidad_reactivaciones=0)
        for fila in desglose:
            _acumular(total, fila)
            clave = fila.id_agencia, fila.codigo_tipo_cuenta
            if clave in por_agencia_tipo:
                _acumular(por_agencia_tipo[clave], fila)
            else:
                responsable = responsables.get(fila.id_agencia, {})
                por_agencia_tipo[clave] = ResumenReactivaciones.model_validate({
                    **fila.model_dump(),
                    "cargo_jefe_agencia": responsable.get("Cargo"),
                    "nombre_jefe_agencia": responsable.get("GerenteOficina"),
                })
        return ConsultaCuentasReactivadasResponse(
            resumen=list(por_agencia_tipo.values()),
            desglose=desglose,
            total=total,
        )

    def detalle(
        self, body: DetalleCuentasReactivadasRequest, auth: AuthContext,
    ) -> DetalleCuentasReactivadasResponse:
        agencias = self._validar_consulta(body, auth)
        filas = self.repositorio.obtener_detalle(
            agencias, body.fecha_inicio, body.fecha_fin,
            cargos=body.cargos, asesores=body.asesores,
            codigo_tipo_cuenta=body.codigo_tipo_cuenta,
            desplazamiento=body.desplazamiento, tamano_pagina=body.tamano_pagina,
            sin_paginacion=body.sin_paginacion,
        )
        return DetalleCuentasReactivadasResponse(
            filas=[ReactivacionDetalle.model_validate(fila) for fila in filas],
        )

    def _validar_consulta(self, body: ConsultaCuentasReactivadas, auth: AuthContext) -> list[int]:
        if body.fecha_fin > fecha_de_sistema(auth):
            raise HTTPException(400, "La fecha final no puede superar la fecha del sistema.")

        agencias = ids_agencia(body)
        habilitadas = {oficina.id for oficina in self.oficinas.get_oficinas_consulta(auth.usuario.sub)}
        if not habilitadas.issuperset(agencias):
            raise HTTPException(403, "La consulta incluye agencias que no tienes habilitadas.")
        return agencias


def _acumular(destino: IndicadoresReactivaciones, fila: IndicadoresReactivaciones) -> None:
    destino.cantidad_cuentas += fila.cantidad_cuentas
    destino.cantidad_reactivaciones += fila.cantidad_reactivaciones
    if fila.total_recaudado is not None:
        destino.total_recaudado = (destino.total_recaudado or 0) + fila.total_recaudado

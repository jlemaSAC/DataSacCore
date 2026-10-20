import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from .domain import (
    CorteCastigoNoDisponibleError,
    CorteDepositosCastigo,
    CortesDepositosCastigo,
)
from .repositories.mongo_castigo_repository import MongoCastigoRepository
from .repositories.sql_castigo_repository import SqlCastigoRepository
from .schemas import (
    DepositoCastigoDiarioOut,
    DepositosCastigoCatalogosOut,
    DepositosCastigoResponse,
    InputDepositosCastigo,
    InputDetalleDepositosCastigo,
    DetalleDepositosCastigoResponse,
    MovimientoDepositoCuentaOut,
)

logger = logging.getLogger("uvicorn.error")


class CastigoService:
    def __init__(
        self,
        mongo_repository: MongoCastigoRepository,
        sql_repository: SqlCastigoRepository,
    ) -> None:
        self.mongo_repository = mongo_repository
        self.sql_repository = sql_repository

    def obtener_depositos_diarios(
        self, input_data: InputDepositosCastigo, auth_context: AuthContext,
        *, numeros_prestamo: list[str] | None = None,
    ) -> DepositosCastigoResponse:
        fecha_sistema = auth_context.usuario.fecha_sistema
        fecha_actual = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        if input_data.fecha_hasta > fecha_actual:
            raise HTTPException(400, "fecha_hasta no puede ser posterior a la fecha del sistema.")
        try:
            datos = self.mongo_repository.obtener_cortes(
                fecha_desde=input_data.fecha_desde, fecha_hasta=input_data.fecha_hasta,
                fecha_actual=fecha_actual, agencias=input_data.agencias,
                asesores=input_data.asesores, cargos=input_data.cargos,
                numeros_prestamo=numeros_prestamo,
            )
            cortes = list(datos.cortes)
            if datos.fecha_sql:
                montos = self.sql_repository.obtener_depositos_mes(
                    [prestamo.numero_prestamo for prestamo in datos.prestamos], datos.fecha_sql,
                )
                for prestamo in datos.prestamos:
                    if prestamo.numero_prestamo not in montos:
                        raise CorteCastigoNoDisponibleError(
                            "No se pudo obtener DepositosMes del corte actual "
                            "para todos los préstamos del universo inicial."
                        )
                    cortes.append(CorteDepositosCastigo(
                        prestamo.numero_prestamo, datos.fecha_sql,
                        montos[prestamo.numero_prestamo],
                        datos.estados_actuales.get(prestamo.numero_prestamo, ""),
                    ))
            depositos = calcular_depositos_diarios(
                datos, cortes, input_data.fecha_desde, input_data.fecha_hasta,
            )
            total = sum((Decimal(str(item.total_depositado)) for item in depositos), Decimal(0))
            return DepositosCastigoResponse(
                fecha_desde=input_data.fecha_desde, fecha_hasta=input_data.fecha_hasta,
                depositos=depositos, total_depositado=float(total),
                catalogos=DepositosCastigoCatalogosOut(
                    agencias=sorted({p.agencia for p in datos.prestamos if p.agencia}),
                    asesores=sorted({p.asesor for p in datos.prestamos if p.asesor}),
                    cargos=sorted({p.cargo for p in datos.prestamos if p.cargo}),
                ),
            )
        except CorteCastigoNoDisponibleError as exc:
            raise HTTPException(409, str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error consultando depósitos mensuales de préstamos castigados")
            raise HTTPException(500, "No fue posible consultar los depósitos diarios de castigo.") from exc

    def obtener_detalle_depositos(
        self, input_data: InputDetalleDepositosCastigo, auth_context: AuthContext,
    ) -> DetalleDepositosCastigoResponse:
        consulta = InputDepositosCastigo(**input_data.model_dump(include={
            "fecha_desde", "fecha_hasta", "agencias", "asesores", "cargos",
        }))
        resultado = self.obtener_depositos_diarios(
            consulta, auth_context, numeros_prestamo=input_data.numeros_prestamo,
        )
        depositos = [d for d in resultado.depositos if d.total_depositado != 0 and (
            input_data.fecha_deposito is None or d.fecha == input_data.fecha_deposito
        )]
        desde = input_data.fecha_deposito or input_data.fecha_desde
        hasta = input_data.fecha_deposito or input_data.fecha_hasta
        numeros = sorted({d.numero_prestamo for d in depositos})
        try:
            if input_data.incluir_movimientos:
                filas, cantidad, creditos = self.sql_repository.obtener_movimientos(
                    numeros, desde, hasta, input_data.pagina, input_data.tamano_pagina,
                )
            else:
                filas, cantidad, creditos = [], 0, Decimal(0)
        except Exception as exc:
            logger.exception("Error consultando movimientos en cuentas para castigo")
            raise HTTPException(500, "No fue posible consultar los movimientos en cuentas.") from exc
        return DetalleDepositosCastigoResponse(
            fecha_desde=desde, fecha_hasta=hasta, depositos=depositos,
            total_depositado=float(sum((Decimal(str(d.total_depositado)) for d in depositos), Decimal(0))),
            movimientos=[MovimientoDepositoCuentaOut(**fila) for fila in filas],
            total_movimientos=cantidad, total_creditos_cuenta=float(creditos),
            pagina=input_data.pagina, tamano_pagina=input_data.tamano_pagina,
        )


def calcular_depositos_diarios(
    datos: CortesDepositosCastigo,
    cortes: list[CorteDepositosCastigo],
    desde: date,
    hasta: date,
) -> list[DepositoCastigoDiarioOut]:
    por_prestamo: dict[str, dict[date, CorteDepositosCastigo]] = {}
    for corte in cortes:
        anteriores = por_prestamo.setdefault(corte.numero_prestamo, {})
        repetido = anteriores.get(corte.fecha)
        if repetido is not None and repetido != corte:
            raise CorteCastigoNoDisponibleError(
                f"Existen cortes contradictorios en {corte.fecha.isoformat()} "
                "para un préstamo del universo inicial."
            )
        anteriores[corte.fecha] = corte
    resultado = []
    for prestamo in datos.prestamos:
        valores = por_prestamo.get(prestamo.numero_prestamo, {})
        base = desde - timedelta(days=1)
        fechas_necesarias = [
            desde + timedelta(days=i) for i in range((hasta - desde).days + 1)
        ]
        if desde.day > 1:
            fechas_necesarias.insert(0, base)
        for fecha in fechas_necesarias:
            if fecha not in valores:
                raise CorteCastigoNoDisponibleError(
                    f"Falta el corte {fecha.isoformat()} de un préstamo del universo inicial; "
                    "no se puede calcular su depósito diario."
                )
        anterior = valores[base].depositos_mes if desde.day > 1 else Decimal(0)
        movimientos = []
        for fecha in fechas_necesarias:
            if fecha < desde:
                continue
            monto = (valores[fecha].depositos_mes - anterior).quantize(Decimal("0.01"))
            anterior = valores[fecha].depositos_mes
            if monto != 0:
                movimientos.append((fecha, monto))
        # Se conserva cada préstamo, incluso si su acumulado y sus variaciones son cero.
        if not movimientos:
            movimientos.append((hasta, Decimal(0)))
        for fecha, monto in movimientos:
            resultado.append(DepositoCastigoDiarioOut(
                numero_prestamo=prestamo.numero_prestamo, fecha=fecha,
                estado_inicio=prestamo.estado, estado_fin=valores[hasta].estado,
                tipo_transaccion="VARIACION DEPOSITOS MES", agencia=prestamo.agencia,
                codigo_asesor=prestamo.codigo_asesor, asesor=prestamo.asesor,
                cargo_asesor=prestamo.cargo, total_depositado=float(monto),
            ))
    resultado.sort(key=lambda deposito: (deposito.fecha, deposito.numero_prestamo))
    return resultado

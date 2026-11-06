from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.ahorro_vista.evaluacion_cuentas_ahorro_vista.repositories.sql_evaluacion_cuentas_ahorro_vista_repository import (
    SqlEvaluacionCuentasAhorroVistaRepository,
)
from app.modules.negocios.ahorro_vista.evaluacion_cuentas_ahorro_vista.schemas import (
    CuentaAhorroVistaComparacion,
    CuentaAhorroVistaValores,
    CuentaAhorroVistaVariacion,
    EvaluacionCuentasAhorroVistaRequest,
    EvaluacionCuentasAhorroVistaResponse,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)


def _valores(fila: dict[str, Any] | None) -> CuentaAhorroVistaValores | None:
    if fila is None:
        return None
    cuentas = int(fila["cuentas"])
    suma = Decimal(str(fila["suma_tasas"]))
    return CuentaAhorroVistaValores(
        saldo=float(Decimal(str(fila["saldo"])).quantize(Decimal("0.01"))),
        cuentas=cuentas, suma_tasas=float(suma),
        tasa_promedio=float((suma / cuentas).quantize(Decimal("0.0001"))) if cuentas else None,
    )


def _diferencia(
    actual: CuentaAhorroVistaValores | None, cierre: CuentaAhorroVistaValores | None,
) -> CuentaAhorroVistaVariacion:
    tasa_actual = actual.tasa_promedio if actual else None
    tasa_cierre = cierre.tasa_promedio if cierre else None
    return CuentaAhorroVistaVariacion(
        saldo=round((actual.saldo if actual else 0) - (cierre.saldo if cierre else 0), 2),
        cuentas=(actual.cuentas if actual else 0) - (cierre.cuentas if cierre else 0),
        tasa_promedio=round(tasa_actual - tasa_cierre, 4)
        if tasa_actual is not None and tasa_cierre is not None else None,
    )


class EvaluacionCuentasAhorroVistaService:
    def __init__(
        self, repository: SqlEvaluacionCuentasAhorroVistaRepository,
        catalogo: SqlSituacionCrediticiaAsesoresRepository,
    ) -> None:
        self.repository = repository
        self.catalogo = catalogo

    def obtener(
        self, body: EvaluacionCuentasAhorroVistaRequest, auth: AuthContext,
    ) -> EvaluacionCuentasAhorroVistaResponse:
        fecha_sistema = auth.usuario.fecha_sistema
        if isinstance(fecha_sistema, datetime):
            fecha_sistema = fecha_sistema.date()
        if body.fecha_fin > fecha_sistema:
            raise HTTPException(400, "fecha_fin no puede superar la fecha del sistema.")
        if body.id_agencia and not self.catalogo.obtener_nombre_agencia(body.id_agencia):
            raise HTTPException(404, "La agencia no existe.")
        fecha_cierre = body.fecha_inicio.replace(day=1) - timedelta(days=1)
        cortes = []
        for fecha in (body.fecha_fin, fecha_cierre):
            corte = self.repository.obtener_corte(
                fecha=fecha, fecha_sistema=fecha_sistema, id_agencia=body.id_agencia,
            )
            if corte is None:
                raise HTTPException(404, f"No existe un cierre de ahorros a la vista disponible para {fecha}.")
            cortes.append(corte)
        actual, cierre = cortes

        def indice(filas: list[dict[str, Any]]) -> dict[tuple[str, int, str], dict[str, Any]]:
            return {
                (str(f["codigo_usuario"]), int(f["id_agencia"]), str(f["codigo_producto"])): f
                for f in filas
            }

        actuales, anteriores = indice(actual.filas), indice(cierre.filas)
        comparacion = []
        for codigo, agencia, producto in sorted(actuales.keys() | anteriores.keys()):
            clave = (codigo, agencia, producto)
            fin, anterior = actuales.get(clave), anteriores.get(clave)
            referencia = fin if fin is not None else anterior
            valores_fin, valores_cierre = _valores(fin), _valores(anterior)
            comparacion.append(CuentaAhorroVistaComparacion(
                clave=f"{codigo}::{agencia}::{producto}", codigo_usuario=codigo,
                id_agencia=agencia, codigo_producto=producto,
                producto_ahorro=referencia["producto_ahorro"],
                nombre_asesor_actual=fin["nombre"] if fin else None,
                nombre_asesor_cierre_mes_anterior=anterior["nombre"] if anterior else None,
                agencia_actual=fin["agencia"] if fin else None,
                agencia_cierre_mes_anterior=anterior["agencia"] if anterior else None,
                valores_actual=valores_fin, valores_cierre_mes_anterior=valores_cierre,
                diferencias_cierre_mes_anterior=_diferencia(valores_fin, valores_cierre),
            ))
        agencias = sorted({str(f["agencia"]) for f in actual.filas + cierre.filas})
        return EvaluacionCuentasAhorroVistaResponse(
            fecha_inicio=body.fecha_inicio, fecha_fin=body.fecha_fin,
            fecha_corte_actual=actual.fecha, fecha_corte_cierre_mes_anterior=cierre.fecha,
            comparacion=comparacion,
            agencias_gerentes_oficina=self.catalogo.obtener_gerentes_oficina(agencias),
            faltantes_en_cierre_mes_anterior=[
                f"{c}::{a}::{p}" for c, a, p in sorted(actuales.keys() - anteriores.keys())
            ],
            faltantes_en_actual=[
                f"{c}::{a}::{p}" for c, a, p in sorted(anteriores.keys() - actuales.keys())
            ],
        )

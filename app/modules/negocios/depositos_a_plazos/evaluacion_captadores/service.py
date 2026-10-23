from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)
from app.modules.negocios.depositos_a_plazos.evaluacion_captadores.repositories.sql_evaluacion_captadores_repository import (
    SqlEvaluacionCaptadoresRepository,
)
from app.modules.negocios.depositos_a_plazos.evaluacion_captadores.schemas import (
    CaptadorComparacion, CaptadorValores, CaptadorVariacion,
    EvaluacionCaptadoresRequest, EvaluacionCaptadoresResponse,
)


def _valores(fila: dict[str, Any] | None) -> CaptadorValores | None:
    if fila is None:
        return None
    operaciones = int(fila["operaciones"])
    ingresos = int(fila["operaciones_renovacion"])
    suma = float(fila["suma_tasas"])
    suma_ingresos = float(fila["suma_tasas_renovacion"])
    return CaptadorValores(
        saldo_deposito=round(float(fila["saldo"]), 2), operaciones=operaciones,
        tasa_promedio=round(suma / operaciones, 4) if operaciones else None,
        tasa_promedio_renovacion=round(suma_ingresos / ingresos, 4) if ingresos else None,
        suma_tasas=suma, operaciones_renovacion=ingresos, suma_tasas_renovacion=suma_ingresos,
    )


def _diferencia(actual: CaptadorValores | None, cierre: CaptadorValores | None) -> CaptadorVariacion:
    def tasa(campo: str) -> float | None:
        a = getattr(actual, campo, None)
        c = getattr(cierre, campo, None)
        return round(a - c, 4) if a is not None and c is not None else None

    return CaptadorVariacion(
        saldo_deposito=round((actual.saldo_deposito if actual else 0) - (cierre.saldo_deposito if cierre else 0), 2),
        operaciones=(actual.operaciones if actual else 0) - (cierre.operaciones if cierre else 0),
        tasa_promedio=tasa("tasa_promedio"),
        tasa_promedio_renovacion=tasa("tasa_promedio_renovacion"),
    )


class EvaluacionCaptadoresService:
    def __init__(
        self, repository: SqlEvaluacionCaptadoresRepository,
        catalogo: SqlSituacionCrediticiaAsesoresRepository,
    ) -> None:
        self.repository = repository
        self.catalogo = catalogo

    def obtener(self, body: EvaluacionCaptadoresRequest, auth: AuthContext) -> EvaluacionCaptadoresResponse:
        fecha_sistema = auth.usuario.fecha_sistema
        if isinstance(fecha_sistema, datetime):
            fecha_sistema = fecha_sistema.date()
        if body.fecha_fin > fecha_sistema:
            raise HTTPException(400, "fecha_fin no puede superar la fecha del sistema.")
        if body.id_agencia and not self.catalogo.obtener_nombre_agencia(body.id_agencia):
            raise HTTPException(404, "La agencia no existe.")
        fecha_cierre = body.fecha_inicio.replace(day=1) - timedelta(days=1)
        actual = self.repository.obtener_corte(
            fecha=body.fecha_fin, fecha_sistema=fecha_sistema,
            fecha_ingreso_desde=body.fecha_inicio, id_agencia=body.id_agencia,
        )
        cierre = self.repository.obtener_corte(
            fecha=fecha_cierre, fecha_sistema=fecha_sistema,
            fecha_ingreso_desde=fecha_cierre.replace(day=1), id_agencia=body.id_agencia,
        )
        if actual is None or cierre is None:
            faltante = body.fecha_fin if actual is None else fecha_cierre
            raise HTTPException(404, f"No existe un cierre de depósitos disponible para {faltante}.")

        def indice(filas: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
            return {(str(f["codigo"]), int(f["IDAGENCIA"])): f for f in filas}

        actuales = indice(actual.filas)
        cierres = indice(cierre.filas)
        comparacion: list[CaptadorComparacion] = []
        for codigo, agencia in sorted(actuales.keys() | cierres.keys()):
            fin = actuales.get((codigo, agencia))
            anterior = cierres.get((codigo, agencia))
            valores_fin, valores_cierre = _valores(fin), _valores(anterior)
            referencia = fin if fin is not None else anterior
            comparacion.append(CaptadorComparacion(
                clave=f"{codigo}::{agencia}", codigo_usuario=codigo,
                nombre_captador_actual=fin["nombre"] if fin else None,
                nombre_captador_cierre_mes_anterior=anterior["nombre"] if anterior else None,
                cargo_captador_actual=referencia["cargo"],
                agencia_actual=fin["agencia"] if fin else None,
                agencia_cierre_mes_anterior=anterior["agencia"] if anterior else None,
                valores_actual=valores_fin, valores_cierre_mes_anterior=valores_cierre,
                diferencias_cierre_mes_anterior=_diferencia(valores_fin, valores_cierre),
            ))
        agencias = sorted({str(f["agencia"]) for f in actual.filas + cierre.filas})
        return EvaluacionCaptadoresResponse(
            fecha_inicio=body.fecha_inicio, fecha_fin=body.fecha_fin,
            fecha_corte_actual=actual.fecha, fecha_corte_cierre_mes_anterior=cierre.fecha,
            comparacion=comparacion,
            agencias_gerentes_oficina=self.catalogo.obtener_gerentes_oficina(agencias),
            faltantes_en_cierre_mes_anterior=[f"{c}::{a}" for c, a in sorted(actuales.keys() - cierres.keys())],
            faltantes_en_actual=[f"{c}::{a}" for c, a in sorted(cierres.keys() - actuales.keys())],
        )

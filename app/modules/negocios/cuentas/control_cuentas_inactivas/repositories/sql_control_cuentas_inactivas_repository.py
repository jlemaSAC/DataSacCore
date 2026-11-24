from calendar import monthrange
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ...schemas import FiltroSaldo
from ...sql_cuentas import (
    AGENCIA_EXPANDIBLE,
    CARGO_OFICIAL,
    NOMBRE_CARGO,
    PREDICADOS_SALDO,
    RESUMEN,
    SALDO_TOTAL_CENTAVOS,
    SALDOS_POR_CUENTA,
    TABLAS_CUENTA_BASE,
    TITULAR_PRINCIPAL,
    filtros_detalle,
)
from ..schemas import TiempoInactividad


# Cada registro conserva el estado anterior. El anterior del siguiente cambio
# revela el estado resultante; el último se resuelve con el estado actual.
_SECUENCIA_INACTIVACION = """
    CambiosCuenta AS (
        SELECT H.NUMEROCUENTA, H.FECHA, H.FECHAPROCESO, H.ID,
               H.CODIGOESTADOCAMBIO AS estado_anterior,
               LEAD(H.CODIGOESTADOCAMBIO, 1, ACTUAL.CODIGOESTADO) OVER (
                   PARTITION BY H.NUMEROCUENTA
                   ORDER BY H.FECHAPROCESO, H.ID
               ) AS estado_resultante
        FROM AHORROS.CUENTAESTADO_HISTORICO AS H
        INNER JOIN {fuente_cuentas} AS ACTUAL ON ACTUAL.NUMERO = H.NUMEROCUENTA
        WHERE ACTUAL.CODIGOESTADO = N'I'
          AND ACTUAL.IDAGENCIA IN :ids_agencia
    ),
    Inactivaciones AS (
        SELECT NUMEROCUENTA, FECHA,
               ROW_NUMBER() OVER (
                   PARTITION BY NUMEROCUENTA
                   ORDER BY FECHAPROCESO DESC, ID DESC
               ) AS orden
        FROM CambiosCuenta
        WHERE estado_anterior <> N'I' AND estado_resultante = N'I'
    ),
    UltimaInactivacion AS (
        SELECT NUMEROCUENTA, FECHA
        FROM Inactivaciones
        WHERE orden = 1
    )
"""
_HISTORIAL_INACTIVACION = _SECUENCIA_INACTIVACION.format(fuente_cuentas="AHORROS.CUENTA")

_TABLAS_CUENTA = TABLAS_CUENTA_BASE + """
    LEFT JOIN UltimaInactivacion AS UI ON UI.NUMEROCUENTA = C.NUMERO
"""

_CUENTAS_INACTIVAS = """
    WHERE C.CODIGOESTADO = N'I'
      AND TC.ESCERTIFICADOAPORTACION = 0
      AND C.IDAGENCIA IN :ids_agencia
"""

_CUENTAS_CANDIDATAS = """
    CuentasCandidatas AS (
        SELECT C.NUMERO, C.IDAGENCIA, C.CODIGOESTADO, C.CODIGOUSUARIOOFICIAL,
               C.CODIGOTIPOCUENTA, C.FECHAULTIMATRANSACCIONACTIVA,
               TC.NOMBRE AS tipo_cuenta
        {tablas_cuenta}
        {fuente_cargo}
        {filtros_cuentas} {filtros_seleccion}
    )
"""

_RANGOS_INACTIVIDAD = {
    "0_1": (0, 1),
    "1_2": (1, 2),
    "2_3": (2, 3),
    "3_6": (3, 6),
    "6_12": (6, 12),
    "12_24": (12, 24),
    "24_36": (24, 36),
    "36_60": (36, 60),
    "mas_60": (60, None),
    "mas_36": (36, None),
}


def _dia_posterior_al_corte(fecha: date, meses: int) -> date:
    anio, mes_cero = divmod(fecha.year * 12 + fecha.month - 1 - meses, 12)
    mes = mes_cero + 1
    ultimo_dia = monthrange(anio, mes)[1]
    # Al cierre del mes, se incluyen los días del mes de origen cuyo aniversario
    # se ajusta al último día, por ejemplo 31 de enero a 28 de febrero.
    es_fin_de_mes = fecha.day == monthrange(fecha.year, fecha.month)[1]
    dia = ultimo_dia if es_fin_de_mes else min(fecha.day, ultimo_dia)
    return date(anio, mes, dia) + timedelta(days=1)


def _filtro_cuentas(
    ids_agencia: list[int], inactividad: TiempoInactividad | list[TiempoInactividad] | None, fecha_sistema: date,
    *, incluir_filtro_cuentas: bool = True,
) -> tuple[str, dict[str, Any]]:
    filtros = _CUENTAS_INACTIVAS if incluir_filtro_cuentas else "WHERE 1 = 1"
    params: dict[str, Any] = {"ids_agencia": ids_agencia}
    rangos = inactividad if isinstance(inactividad, list) else ([inactividad] if inactividad else [])
    predicados = []
    for indice, rango in enumerate(dict.fromkeys(rangos)):
        if rango == "sin_fecha":
            predicados.append("UI.FECHA IS NULL")
            continue
        meses_min, meses_max = _RANGOS_INACTIVIDAD[rango]
        # Los rangos tienen límite superior exclusivo, salvo 36_60 que incluye
        # el aniversario de 60 meses para que mas_60 empiece al día siguiente.
        dia_anterior = fecha_sistema - timedelta(days=1)
        referencia_min = dia_anterior if rango in ("mas_36", "mas_60") else fecha_sistema
        sufijo = f"_{indice}" if isinstance(inactividad, list) else ""
        hasta = f"fecha_hasta_exclusiva{sufijo}"
        predicado = f"UI.FECHA < :{hasta}"
        params[hasta] = _dia_posterior_al_corte(referencia_min, meses_min)
        if meses_max is not None:
            referencia_max = dia_anterior if rango == "36_60" else fecha_sistema
            desde = f"fecha_desde_inclusiva{sufijo}"
            predicado += f" AND UI.FECHA >= :{desde}"
            params[desde] = _dia_posterior_al_corte(referencia_max, meses_max)
        predicados.append(f"({predicado})")
    if predicados:
        filtros += " AND (" + " OR ".join(predicados) + ")"
    return filtros, params


class SqlControlCuentasInactivasRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_desglose(
        self, ids_agencia: list[int], *, fecha_sistema: date,
        inactividad: TiempoInactividad | list[TiempoInactividad] | None, saldo: FiltroSaldo | None,
    ) -> Sequence[Mapping[str, Any]]:
        filtros, params = _filtro_cuentas(
            ids_agencia, inactividad, fecha_sistema, incluir_filtro_cuentas=False,
        )
        ctes_cuentas = _CUENTAS_CANDIDATAS.format(
            tablas_cuenta=TABLAS_CUENTA_BASE, fuente_cargo="",
            filtros_cuentas=_CUENTAS_INACTIVAS, filtros_seleccion="",
        )
        fuente_cuentas = "CuentasCandidatas"
        # Sin rango de inactividad, el resumen no necesita consultar el histórico.
        if inactividad:
            ctes_cuentas += f""",
                {_SECUENCIA_INACTIVACION.format(fuente_cuentas="CuentasCandidatas")},
                CuentasFiltradas AS (
                    SELECT C.*
                    FROM CuentasCandidatas AS C
                    LEFT JOIN UltimaInactivacion AS UI ON UI.NUMEROCUENTA = C.NUMERO
                    {filtros}
                )
            """
            fuente_cuentas = "CuentasFiltradas"
        consulta = text(RESUMEN.format(
            ctes_cuentas=ctes_cuentas,
            fuente_cuentas=fuente_cuentas,
            saldos_por_cuenta=SALDOS_POR_CUENTA,
            predicado_saldo=PREDICADOS_SALDO[saldo],
            valor_total_cuenta=SALDO_TOTAL_CENTAVOS if saldo else "COALESCE(S.total, 0)",
            nombre_cargo=NOMBRE_CARGO,
            cargo_oficial=CARGO_OFICIAL.format(usuario="X.codigo_oficial"),
        )).bindparams(AGENCIA_EXPANDIBLE)
        return self.db.execute(consulta, params).mappings().all()

    def obtener_detalle(
        self, *, ids_agencia: list[int], codigo_oficial: str | None,
        codigo_tipo_cuenta: str | None, pagina: int, tamano_pagina: int,
        fecha_sistema: date, inactividad: TiempoInactividad | list[TiempoInactividad] | None, saldo: FiltroSaldo | None,
        cargos: list[str], asesores: list[str], sin_paginacion: bool = False,
    ) -> tuple[int, Sequence[Mapping[str, Any]]]:
        # Solo se agregan predicados constantes. Los datos se pasan como parámetros.
        filtros, params = _filtro_cuentas(ids_agencia, inactividad, fecha_sistema)
        fuente_cargo, filtros_seleccion, parametros_expandibles = filtros_detalle(
            params, codigo_oficial=codigo_oficial, codigo_tipo_cuenta=codigo_tipo_cuenta,
            cargos=cargos, asesores=asesores,
        )

        predicado_saldo = PREDICADOS_SALDO[saldo]
        if sin_paginacion:
            filtro_fecha, _ = _filtro_cuentas(
                ids_agencia, inactividad, fecha_sistema, incluir_filtro_cuentas=False,
            )
            # Una sola consulta. El histórico se reconstruye únicamente para las
            # cuentas candidatas y los saldos se agregan una vez por cuenta.
            candidatas = _CUENTAS_CANDIDATAS.format(
                tablas_cuenta=TABLAS_CUENTA_BASE, fuente_cargo=fuente_cargo,
                filtros_cuentas=_CUENTAS_INACTIVAS, filtros_seleccion=filtros_seleccion,
            )
            consulta = text(f"""
                WITH {candidatas},
                {_SECUENCIA_INACTIVACION.format(fuente_cuentas="CuentasCandidatas")},
                Seleccion AS (
                    SELECT C.*, UI.FECHA AS fecha_inactivacion,
                           S.disponible, S.total
                    FROM CuentasCandidatas AS C
                    LEFT JOIN UltimaInactivacion AS UI ON UI.NUMEROCUENTA = C.NUMERO
                    {SALDOS_POR_CUENTA}
                    {filtro_fecha} {predicado_saldo}
                )
                SELECT C.NUMERO AS numero_cuenta, A.NOMBRE AS agencia,
                       U.NOMBRE AS oficial, C.tipo_cuenta, T.titular,
                       CAST(C.FECHAULTIMATRANSACCIONACTIVA AS date) AS ultima_transaccion_activa,
                       CAST(C.fecha_inactivacion AS date) AS fecha_inactivacion,
                       DATEDIFF(day, C.fecha_inactivacion, :fecha_sistema) AS dias_inactividad,
                       COALESCE(C.disponible, 0) AS valor_disponible,
                       COALESCE(C.total, 0) AS valor_total
                FROM Seleccion AS C
                INNER JOIN GENERAL.AGENCIA AS A ON A.ID = C.IDAGENCIA
                INNER JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = C.CODIGOUSUARIOOFICIAL
                {TITULAR_PRINCIPAL}
                ORDER BY C.NUMERO
            """).bindparams(*parametros_expandibles)
            filas = self.db.execute(consulta, {**params, "fecha_sistema": fecha_sistema}).mappings().all()
            return len(filas), filas

        filtros += filtros_seleccion
        # Con filtro de saldo se evalúan todas las candidatas antes de paginar.
        # En la consulta normal solo se calculan los saldos de la página.
        fuente = _TABLAS_CUENTA + fuente_cargo + (SALDOS_POR_CUENTA if predicado_saldo else "")
        filtros += predicado_saldo
        fuente_conteo = fuente
        historial_conteo = f"WITH {_HISTORIAL_INACTIVACION}"
        if not inactividad:
            fuente_conteo = TABLAS_CUENTA_BASE + fuente_cargo + (
                SALDOS_POR_CUENTA if predicado_saldo else ""
            )
            historial_conteo = ""
        conteo = text(f"""
            {historial_conteo}
            SELECT COUNT_BIG(*) {fuente_conteo} {filtros}
        """).bindparams(*parametros_expandibles)
        total = self.db.execute(conteo, params).scalar_one()
        desplazamiento = (pagina - 1) * tamano_pagina
        if desplazamiento >= total:
            return total, []

        columnas_saldo = ", S.disponible, S.total" if predicado_saldo else ""
        alias_saldo = "C" if predicado_saldo else "S"
        saldos_pagina = "" if predicado_saldo else SALDOS_POR_CUENTA
        consulta = text(f"""
            WITH {_HISTORIAL_INACTIVACION},
            CuentasPagina AS (
                SELECT C.NUMERO, C.IDAGENCIA, C.CODIGOUSUARIOOFICIAL, TC.NOMBRE AS tipo_cuenta,
                       C.FECHAULTIMATRANSACCIONACTIVA, UI.FECHA AS fecha_inactivacion {columnas_saldo}
                {fuente}
                {filtros}
                ORDER BY C.NUMERO
                OFFSET :desplazamiento ROWS FETCH NEXT :limite ROWS ONLY
            )
            SELECT C.NUMERO AS numero_cuenta, A.NOMBRE AS agencia, T.titular,
                   U.NOMBRE AS oficial, C.tipo_cuenta,
                   CAST(C.FECHAULTIMATRANSACCIONACTIVA AS date) AS ultima_transaccion_activa,
                   CAST(C.fecha_inactivacion AS date) AS fecha_inactivacion,
                   DATEDIFF(day, C.fecha_inactivacion, :fecha_sistema) AS dias_inactividad,
                   COALESCE({alias_saldo}.disponible, 0) AS valor_disponible,
                   COALESCE({alias_saldo}.total, 0) AS valor_total
            FROM CuentasPagina AS C
            INNER JOIN GENERAL.AGENCIA AS A ON A.ID = C.IDAGENCIA
            INNER JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = C.CODIGOUSUARIOOFICIAL
            {TITULAR_PRINCIPAL}
            {saldos_pagina}
            ORDER BY C.NUMERO
        """).bindparams(*parametros_expandibles)
        filas = self.db.execute(consulta, {
            **params, "fecha_sistema": fecha_sistema,
            "desplazamiento": desplazamiento, "limite": tamano_pagina,
        }).mappings().all()
        return total, filas

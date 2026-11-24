from typing import Any

from sqlalchemy import bindparam
from sqlalchemy.sql.elements import BindParameter


TABLAS_CUENTA_BASE = """
    FROM AHORROS.CUENTA AS C
    INNER JOIN AHORROS.TIPO_CUENTA AS TC
        ON TC.CODIGO = C.CODIGOTIPOCUENTA
    INNER JOIN GENERAL.MONEDA AS M
        ON M.ID = C.IDMONEDA AND M.CODIGO = N'USD'
"""


AGENCIA_EXPANDIBLE = bindparam("ids_agencia", expanding=True)


CARGO_OFICIAL = """
    OUTER APPLY (
        SELECT TOP (1) CARGO.NOMBRE
        FROM NOMINA.EMPLEADO_USUARIO AS EU
        INNER JOIN NOMINA.EMPLEADO AS E ON E.ID = EU.IDEMPLEADO
        INNER JOIN NOMINA.CARGO AS CARGO ON CARGO.ID = E.IDCARGO
        WHERE EU.CODIGOUSUARIO = {usuario}
        ORDER BY E.FECHAPROCESO DESC, E.ID DESC
    ) AS Cargo
"""


NOMBRE_CARGO = "COALESCE(NULLIF(LTRIM(RTRIM(Cargo.NOMBRE)), N''), N'SIN CARGO')"


TITULAR_PRINCIPAL = """
    OUTER APPLY (
        SELECT TOP (1) P.NOMBRE AS titular
        FROM AHORROS.CUENTA_CLIENTE AS CC
        INNER JOIN CLIENTES.CLIENTE AS CL ON CL.ID = CC.IDCLIENTE
        INNER JOIN SUJETO.PERSONA AS P ON P.ID = CL.IDPERSONA
        WHERE CC.NUMEROCUENTA = C.NUMERO AND CC.PRINCIPAL = 1
        ORDER BY CC.IDCLIENTE
    ) AS T
"""


SALDOS_POR_CUENTA = """
    OUTER APPLY (
        SELECT SUM(CASE WHEN TI.ESDISPONIBLE = 1 THEN CI.SALDO ELSE 0 END) AS disponible,
               SUM(CI.SALDO) AS total
        FROM AHORROS.CUENTA_ITEMSALDO AS CI
        INNER JOIN AHORROS.ITEMSALDO AS I ON I.ID = CI.IDITEM
        INNER JOIN AHORROS.TIPO_ITEMSALDO AS TI ON TI.ID = I.IDTIPOITEM
        WHERE CI.NUMEROCUENTA = C.NUMERO AND I.SUMASALDO = 1
    ) AS S
"""


SALDO_TOTAL_CENTAVOS = "ROUND(COALESCE(S.total, 0), 2)"


PREDICADOS_SALDO = {
    None: "",
    "cero": f" AND {SALDO_TOTAL_CENTAVOS} = 0",
    "con_saldo": f" AND {SALDO_TOTAL_CENTAVOS} <> 0",
}


RESUMEN = """
    WITH {ctes_cuentas},
    Agrupados AS (
    SELECT C.IDAGENCIA AS id_agencia, A.NOMBRE AS agencia,
           C.CODIGOUSUARIOOFICIAL AS codigo_oficial, U.NOMBRE AS oficial,
           C.CODIGOTIPOCUENTA AS codigo_tipo_cuenta, C.tipo_cuenta,
           COUNT_BIG(*) AS cantidad_cuentas,
           SUM(COALESCE(S.disponible, 0)) AS valor_disponible,
           SUM({valor_total_cuenta}) AS valor_total
    FROM {fuente_cuentas} AS C
    INNER JOIN GENERAL.AGENCIA AS A ON A.ID = C.IDAGENCIA
    INNER JOIN SEGURIDAD.USUARIO AS U ON U.USUARIO = C.CODIGOUSUARIOOFICIAL
    {saldos_por_cuenta}
    WHERE 1 = 1 {predicado_saldo}
    GROUP BY C.IDAGENCIA, A.NOMBRE, C.CODIGOUSUARIOOFICIAL,
             U.NOMBRE, C.CODIGOTIPOCUENTA, C.tipo_cuenta
    )
    SELECT X.*, {nombre_cargo} AS cargo
    FROM Agrupados AS X
    {cargo_oficial}
"""


def filtros_detalle(
    params: dict[str, Any], *, codigo_oficial: str | None, codigo_tipo_cuenta: str | None,
    cargos: list[str], asesores: list[str],
) -> tuple[str, str, list[BindParameter]]:
    parametros_expandibles = [AGENCIA_EXPANDIBLE]
    fuente_cargo = ""
    filtros_seleccion = ""
    if cargos:
        fuente_cargo = CARGO_OFICIAL.format(usuario="C.CODIGOUSUARIOOFICIAL")
        filtros_seleccion += f" AND {NOMBRE_CARGO} IN :cargos"
        params["cargos"] = cargos
        parametros_expandibles.append(bindparam("cargos", expanding=True))
    if asesores:
        filtros_seleccion += " AND C.CODIGOUSUARIOOFICIAL IN :asesores"
        params["asesores"] = asesores
        parametros_expandibles.append(bindparam("asesores", expanding=True))
    if codigo_oficial is not None:
        filtros_seleccion += " AND C.CODIGOUSUARIOOFICIAL = :codigo_oficial"
        params["codigo_oficial"] = codigo_oficial
    if codigo_tipo_cuenta is not None:
        filtros_seleccion += " AND C.CODIGOTIPOCUENTA = :codigo_tipo_cuenta"
        params["codigo_tipo_cuenta"] = codigo_tipo_cuenta
    return fuente_cargo, filtros_seleccion, parametros_expandibles

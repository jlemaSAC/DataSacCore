/*
    Verificación focalizada de saldo al 2026-07-31.

    A. Criterio correcto de comprobacion.sql:
       cuenta contable 2101351505.
    B. Criterio vigente de REPORTE_ANALITICO_AHORROS_VISTA:
       producto_ahorro = AHORROS.TIPO_CUENTA.NOMBRE = Cuenta Taitita.

    El bloque B replica la fuente de saldo del SP: ITEMSALDO.SUMASALDO = 1.
    No modifica datos ni el procedimiento almacenado.
*/
SET NOCOUNT ON;

DECLARE @FechaCorte date = '2026-07-31';
DECLARE @CuentaContable nvarchar(50) = N'2101351505';
DECLARE @ProductoAhorro nvarchar(150) = N'Cuenta Taitita';
DECLARE @FechaCierreVista datetime;

SELECT @FechaCierreVista = MAX(ECH.FECHACIERREVISTA)
FROM GENERAL.EMPRESA_CIERREHISTORICO AS ECH
WHERE CAST(ECH.FECHASISTEMA AS date) = @FechaCorte;

IF @FechaCierreVista IS NULL
BEGIN
    RAISERROR('No existe FECHACIERREVISTA para la fecha de corte indicada.', 16, 1);
    RETURN;
END;

CREATE TABLE #ComprobacionCorrecta (
    NumeroCuenta nvarchar(50) NOT NULL PRIMARY KEY,
    Saldo decimal(18, 6) NOT NULL
);

/* Estados A/B: INNER JOIN al mapeo contable, igual que comprobacion.sql. */
INSERT INTO #ComprobacionCorrecta (NumeroCuenta, Saldo)
SELECT CM.NUMERO, SUM(CI.SALDO)
FROM AHORROS.CUENTA FOR SYSTEM_TIME AS OF @FechaCierreVista AS CM
INNER JOIN AHORROS.CUENTA_ITEMSALDO FOR SYSTEM_TIME AS OF @FechaCierreVista AS CI
    ON CI.NUMEROCUENTA = CM.NUMERO
INNER JOIN AHORROS.ITEMSALDO_CUENTACONTABLE AS ICC
    ON ICC.IDITEM = CI.IDITEM
   AND ICC.CODIGOCUENTACONTABLE = @CuentaContable
INNER JOIN AHORROS.CUENTA_CLIENTE AS CuentaCliente
    ON CuentaCliente.NUMEROCUENTA = CM.NUMERO
   AND CuentaCliente.PRINCIPAL = 1
INNER JOIN CLIENTES.CLIENTE AS Cliente
    ON Cliente.ID = CuentaCliente.IDCLIENTE
INNER JOIN SUJETO.PERSONA AS Persona
    ON Persona.ID = Cliente.IDPERSONA
WHERE CM.CODIGOTIPOCUENTA <> N'2101350505'
  AND CM.CODIGOESTADO IN (N'A', N'B')
GROUP BY CM.NUMERO;

/* Estado I: COALESCE del mapeo activo/inactivo, igual que comprobacion.sql. */
INSERT INTO #ComprobacionCorrecta (NumeroCuenta, Saldo)
SELECT CM.NUMERO, SUM(CI.SALDO)
FROM AHORROS.CUENTA FOR SYSTEM_TIME AS OF @FechaCierreVista AS CM
INNER JOIN AHORROS.CUENTA_ITEMSALDO FOR SYSTEM_TIME AS OF @FechaCierreVista AS CI
    ON CI.NUMEROCUENTA = CM.NUMERO
LEFT JOIN AHORROS.ITEMSALDO_CUENTACONTABLE AS ICC
    ON ICC.IDITEM = CI.IDITEM
LEFT JOIN AHORROS.ITEMSALDO_CUENTACONTABLE_INACTIVA AS ICCI
    ON ICCI.IDITEM = CI.IDITEM
INNER JOIN AHORROS.CUENTA_CLIENTE AS CuentaCliente
    ON CuentaCliente.NUMEROCUENTA = CM.NUMERO
   AND CuentaCliente.PRINCIPAL = 1
INNER JOIN CLIENTES.CLIENTE AS Cliente
    ON Cliente.ID = CuentaCliente.IDCLIENTE
INNER JOIN SUJETO.PERSONA AS Persona
    ON Persona.ID = Cliente.IDPERSONA
WHERE CM.CODIGOTIPOCUENTA <> N'2101350505'
  AND CM.CODIGOESTADO = N'I'
  AND COALESCE(ICCI.CODIGOCUENTACONTABLE, ICC.CODIGOCUENTACONTABLE) = @CuentaContable
GROUP BY CM.NUMERO;

CREATE TABLE #SaldoSpCuentaTaitita (
    NumeroCuenta nvarchar(50) NOT NULL PRIMARY KEY,
    Saldo decimal(18, 6) NOT NULL
);

/* Replica el saldo del SP para producto_ahorro = Cuenta Taitita. */
INSERT INTO #SaldoSpCuentaTaitita (NumeroCuenta, Saldo)
SELECT CU.NUMERO, SUM(CI.SALDO)
FROM AHORROS.CUENTA FOR SYSTEM_TIME AS OF @FechaCierreVista AS CU
INNER JOIN AHORROS.TIPO_CUENTA AS TC
    ON TC.CODIGO = CU.CODIGOTIPOCUENTA
INNER JOIN AHORROS.CUENTA_CLIENTE AS CuentaCliente
    ON CuentaCliente.NUMEROCUENTA = CU.NUMERO
   AND CuentaCliente.PRINCIPAL = 1
INNER JOIN CLIENTES.CLIENTE AS Cliente
    ON Cliente.ID = CuentaCliente.IDCLIENTE
INNER JOIN SUJETO.PERSONA AS Persona
    ON Persona.ID = Cliente.IDPERSONA
INNER JOIN AHORROS.CUENTA_ITEMSALDO FOR SYSTEM_TIME AS OF @FechaCierreVista AS CI
    ON CI.NUMEROCUENTA = CU.NUMERO
INNER JOIN AHORROS.ITEMSALDO AS ISa
    ON ISa.ID = CI.IDITEM
   AND ISa.SUMASALDO = 1
WHERE CU.CODIGOESTADO IN (N'A', N'B', N'I')
  AND CU.CODIGOTIPOCUENTA <> N'001'
  AND TC.NOMBRE = @ProductoAhorro
GROUP BY CU.NUMERO;

/* Totales a contrastar. */
SELECT
    N'comprobacion.sql / cuenta contable 2101351505' AS criterio,
    COUNT(*) AS cuentas,
    SUM(Saldo) AS saldo
FROM #ComprobacionCorrecta
UNION ALL
SELECT
    N'SP / producto_ahorro Cuenta Taitita',
    COUNT(*),
    SUM(Saldo)
FROM #SaldoSpCuentaTaitita;

/* Cuentas presentes en uno de los criterios o con saldo diferente. */
SELECT
    COALESCE(Comp.NumeroCuenta, Sp.NumeroCuenta) AS numero_cuenta,
    COALESCE(Comp.Saldo, 0) AS saldo_comprobacion,
    COALESCE(Sp.Saldo, 0) AS saldo_sp,
    COALESCE(Comp.Saldo, 0) - COALESCE(Sp.Saldo, 0) AS diferencia
FROM #ComprobacionCorrecta AS Comp
FULL OUTER JOIN #SaldoSpCuentaTaitita AS Sp
    ON Sp.NumeroCuenta = Comp.NumeroCuenta
WHERE COALESCE(Comp.Saldo, 0) <> COALESCE(Sp.Saldo, 0)
   OR Comp.NumeroCuenta IS NULL
   OR Sp.NumeroCuenta IS NULL
ORDER BY ABS(COALESCE(Comp.Saldo, 0) - COALESCE(Sp.Saldo, 0)) DESC,
         COALESCE(Comp.NumeroCuenta, Sp.NumeroCuenta);

DROP TABLE #SaldoSpCuentaTaitita;
DROP TABLE #ComprobacionCorrecta;

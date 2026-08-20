/*
    Verificación de saldo por ítem para ahorros a la vista.

    Compara dos criterios sobre el mismo cierre histórico:
      1. SP analítico: solo AHORROS.ITEMSALDO.SUMASALDO = 1.
      2. comprobacion.sql:
         - cuentas A/B: ítems con mapeo en ITEMSALDO_CUENTACONTABLE.
         - cuentas I: todos los ítems (sus mapeos son LEFT JOIN).

    No modifica datos.
*/
SET NOCOUNT ON;

DECLARE @FechaCorte date = '2026-07-31';

/*
   Asigne un código si desea limitar ambos criterios a un tipo de cuenta.
   Ejemplos:
     N'001'        -- filtro actual del SP.
     N'2101350505' -- filtro de comprobacion.sql.
*/
DECLARE @TipoCuentaExcluir nvarchar(50) = NULL;

DECLARE @FechaCierreVista datetime;

SELECT @FechaCierreVista = MAX(ECH.FECHACIERREVISTA)
FROM GENERAL.EMPRESA_CIERREHISTORICO AS ECH
WHERE CAST(ECH.FECHASISTEMA AS date) = @FechaCorte;

IF @FechaCierreVista IS NULL
BEGIN
    RAISERROR('No existe FECHACIERREVISTA para la fecha de corte indicada.', 16, 1);
    RETURN;
END;

CREATE TABLE #ItemsCuenta (
    NumeroCuenta nvarchar(50) NOT NULL,
    CodigoEstado nvarchar(10) NOT NULL,
    CodigoTipoCuenta nvarchar(50) NOT NULL,
    IdItem int NOT NULL,
    NombreItem nvarchar(150) NULL,
    SumaSaldo bit NOT NULL,
    Saldo decimal(18, 6) NOT NULL,
    TieneMapeoContable bit NOT NULL,
    IncluidoComprobacion bit NOT NULL,
    PRIMARY KEY (NumeroCuenta, IdItem)
);

INSERT INTO #ItemsCuenta (
    NumeroCuenta, CodigoEstado, CodigoTipoCuenta, IdItem, NombreItem,
    SumaSaldo, Saldo, TieneMapeoContable, IncluidoComprobacion
)
SELECT
    CU.NUMERO,
    CU.CODIGOESTADO,
    CU.CODIGOTIPOCUENTA,
    CI.IDITEM,
    ISa.NOMBRE,
    CONVERT(bit, ISa.SUMASALDO),
    CI.SALDO,
    CONVERT(bit, CASE WHEN EXISTS (
        SELECT 1
        FROM AHORROS.ITEMSALDO_CUENTACONTABLE AS ICC
        WHERE ICC.IDITEM = CI.IDITEM
    ) THEN 1 ELSE 0 END),
    CONVERT(bit, CASE
        WHEN CU.CODIGOESTADO IN (N'A', N'B')
         AND EXISTS (
            SELECT 1
            FROM AHORROS.ITEMSALDO_CUENTACONTABLE AS ICC
            WHERE ICC.IDITEM = CI.IDITEM
         ) THEN 1
        WHEN CU.CODIGOESTADO = N'I' THEN 1
        ELSE 0
    END)
FROM AHORROS.CUENTA FOR SYSTEM_TIME AS OF @FechaCierreVista AS CU
INNER JOIN AHORROS.CUENTA_ITEMSALDO FOR SYSTEM_TIME AS OF @FechaCierreVista AS CI
    ON CI.NUMEROCUENTA = CU.NUMERO
INNER JOIN AHORROS.ITEMSALDO AS ISa
    ON ISa.ID = CI.IDITEM
WHERE CU.CODIGOESTADO IN (N'A', N'B', N'I')
  AND (@TipoCuentaExcluir IS NULL OR CU.CODIGOTIPOCUENTA <> @TipoCuentaExcluir);

/* 1. Totales generales por criterio. */
SELECT
    N'SP: SUMASALDO = 1' AS criterio,
    COUNT(DISTINCT NumeroCuenta) AS cuentas,
    SUM(Saldo) AS saldo
FROM #ItemsCuenta
WHERE SumaSaldo = 1
UNION ALL
SELECT
    N'comprobacion.sql: mapeo A/B + todos los ítems I',
    COUNT(DISTINCT NumeroCuenta),
    SUM(Saldo)
FROM #ItemsCuenta
WHERE IncluidoComprobacion = 1;

/* 2. Ítems y su aporte en cada criterio. */
SELECT
    IdItem,
    NombreItem,
    SumaSaldo,
    TieneMapeoContable,
    COUNT(DISTINCT NumeroCuenta) AS cuentas,
    SUM(Saldo) AS saldo_total,
    SUM(CASE WHEN SumaSaldo = 1 THEN Saldo ELSE 0 END) AS saldo_sp,
    SUM(CASE WHEN IncluidoComprobacion = 1 THEN Saldo ELSE 0 END) AS saldo_comprobacion
FROM #ItemsCuenta
GROUP BY IdItem, NombreItem, SumaSaldo, TieneMapeoContable
ORDER BY ABS(SUM(CASE WHEN SumaSaldo = 1 THEN Saldo ELSE 0 END)
           - SUM(CASE WHEN IncluidoComprobacion = 1 THEN Saldo ELSE 0 END)) DESC,
         NombreItem;

/* 3. Primeras 200 cuentas cuyo saldo difiere entre ambos criterios. */
;WITH SaldoSp AS (
    SELECT NumeroCuenta, SUM(Saldo) AS saldo_sp
    FROM #ItemsCuenta
    WHERE SumaSaldo = 1
    GROUP BY NumeroCuenta
),
SaldoComprobacion AS (
    SELECT NumeroCuenta, SUM(Saldo) AS saldo_comprobacion
    FROM #ItemsCuenta
    WHERE IncluidoComprobacion = 1
    GROUP BY NumeroCuenta
)
SELECT TOP (200)
    COALESCE(Sp.NumeroCuenta, Comp.NumeroCuenta) AS numero_cuenta,
    COALESCE(Sp.saldo_sp, 0) AS saldo_sp,
    COALESCE(Comp.saldo_comprobacion, 0) AS saldo_comprobacion,
    COALESCE(Sp.saldo_sp, 0) - COALESCE(Comp.saldo_comprobacion, 0) AS diferencia
FROM SaldoSp AS Sp
FULL OUTER JOIN SaldoComprobacion AS Comp
    ON Comp.NumeroCuenta = Sp.NumeroCuenta
WHERE COALESCE(Sp.saldo_sp, 0) <> COALESCE(Comp.saldo_comprobacion, 0)
ORDER BY ABS(COALESCE(Sp.saldo_sp, 0) - COALESCE(Comp.saldo_comprobacion, 0)) DESC,
         COALESCE(Sp.NumeroCuenta, Comp.NumeroCuenta);

/* 4. Detalle de ítems para una cuenta encontrada en el bloque anterior. */
-- DECLARE @NumeroCuenta nvarchar(50) = N'...';
-- SELECT *
-- FROM #ItemsCuenta
-- WHERE NumeroCuenta = @NumeroCuenta
-- ORDER BY IdItem;

DROP TABLE #ItemsCuenta;

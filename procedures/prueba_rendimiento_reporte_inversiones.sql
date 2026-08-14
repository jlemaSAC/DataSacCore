/*
    Diagnóstico de rendimiento para el reporte analítico de inversiones.
    No modifica tablas persistentes; solo crea tablas temporales de sesión.

    Ejecutar con el plan de ejecución real habilitado (Ctrl+M en SSMS) y
    compartir la cuadrícula final METRICAS y los mensajes STATISTICS IO/TIME.
*/

SET NOCOUNT ON;
SET STATISTICS IO ON;
SET STATISTICS TIME ON;

DECLARE @FechaCorte date = '2026-07-29';
DECLARE @FechaCierrePlazo datetime;
DECLARE @FechaCierreColocacion datetime;
DECLARE @InicioEtapa datetime2(7);
DECLARE @Filas bigint;

SELECT
    @FechaCierrePlazo = ECH.FECHACIERREPLAZO,
    @FechaCierreColocacion = ECH.FECHACIERRECOLOCACION
FROM GENERAL.EMPRESA_CIERREHISTORICO AS ECH WITH (NOLOCK)
WHERE CAST(ECH.FECHASISTEMA AS date) = @FechaCorte;

IF @FechaCierrePlazo IS NULL OR @FechaCierreColocacion IS NULL
    THROW 50000, 'No existe cierre de plazo o colocación para la fecha de corte.', 1;

DROP TABLE IF EXISTS #Metricas;
DROP TABLE IF EXISTS #DepositosCorte;
DROP TABLE IF EXISTS #PrestamosPorCliente;
DROP TABLE IF EXISTS #Periodicidades;
DROP TABLE IF EXISTS #Bandas;
DROP TABLE IF EXISTS #Renovaciones;

CREATE TABLE #Metricas (
    etapa nvarchar(100) NOT NULL,
    filas bigint NOT NULL,
    duracion_ms bigint NOT NULL
);

/* 1. Una única lectura temporal de depósitos del corte. */
SET @InicioEtapa = SYSDATETIME();

SELECT
    D.ID AS id_deposito,
    D.MONTO AS saldo,
    D.IDAGENCIA AS id_agencia,
    D.CODIGOUSUARIO AS codigo_usuario,
    D.CODIGOTIPODEPOSITO AS codigo_tipo_deposito,
    D.CODIGOESTADODEPOSITO AS codigo_estado_deposito,
    D.TASA AS tasa_normal,
    D.VARIACION_TASA AS tasa_variacion,
    C.ID AS id_cliente,
    Persona.IDRESIDENCIA AS id_residencia
INTO #DepositosCorte
FROM INVERSION.DEPOSITO FOR SYSTEM_TIME AS OF @FechaCierrePlazo AS D
INNER JOIN INVERSION.DEPOSITO_CLIENTE AS DC WITH (NOLOCK)
    ON DC.IDDEPOSITO = D.ID
   AND DC.ESPRINCIPAL = 1
   AND DC.ACTIVO = 1
INNER JOIN CLIENTES.CLIENTE AS C WITH (NOLOCK)
    ON C.ID = DC.IDCLIENTE
INNER JOIN SUJETO.PERSONA AS Persona WITH (NOLOCK)
    ON Persona.ID = C.IDPERSONA
WHERE D.CODIGOESTADODEPOSITO IN ('A', 'E');

CREATE UNIQUE CLUSTERED INDEX CIX_DepositosCorte
    ON #DepositosCorte (id_deposito);
CREATE NONCLUSTERED INDEX IX_DepositosCorte_Cliente
    ON #DepositosCorte (id_cliente);

SET @Filas = (SELECT COUNT(*) FROM #DepositosCorte);
INSERT INTO #Metricas (etapa, filas, duracion_ms)
VALUES (
    '1. Depositos historicos',
    @Filas,
    DATEDIFF_BIG(millisecond, @InicioEtapa, SYSDATETIME())
);

/* 2. Una única lectura temporal de préstamos, agrupada por cliente. */
SET @InicioEtapa = SYSDATETIME();

SELECT
    PC.IDCLIENTE AS id_cliente,
    SUM(P.SALDO) AS saldo_prestamo
INTO #PrestamosPorCliente
FROM COLOCACION.PRESTAMO FOR SYSTEM_TIME AS OF @FechaCierreColocacion AS P
INNER JOIN COLOCACION.PRESTAMO_CLIENTE AS PC WITH (NOLOCK)
    ON PC.IDPRESTAMO = P.ID
   AND PC.ACTIVO = 1
INNER JOIN #DepositosCorte AS D
    ON D.id_cliente = PC.IDCLIENTE
WHERE P.CODIGOESTADO <> 'C'
GROUP BY PC.IDCLIENTE;

CREATE UNIQUE CLUSTERED INDEX CIX_PrestamosPorCliente
    ON #PrestamosPorCliente (id_cliente);

SET @Filas = (SELECT COUNT(*) FROM #PrestamosPorCliente);
INSERT INTO #Metricas (etapa, filas, duracion_ms)
VALUES (
    '2. Prestamos historicos por cliente',
    @Filas,
    DATEDIFF_BIG(millisecond, @InicioEtapa, SYSDATETIME())
);

/* 3. Relaciones no temporales, restringidas a los depósitos del corte. */
SET @InicioEtapa = SYSDATETIME();

SELECT
    DFP.IDDEPOSITO AS id_deposito,
    MAX(FP.NOMBRE) AS periodicidad_pago
INTO #Periodicidades
FROM INVERSION.DEPOSITO_FRECUENCIA_PAGO AS DFP WITH (NOLOCK)
INNER JOIN #DepositosCorte AS D
    ON D.id_deposito = DFP.IDDEPOSITO
INNER JOIN INVERSION.FRECUENCIA_PAGO AS FP WITH (NOLOCK)
    ON FP.CODIGO = DFP.CODIGOFRECUENCIAPAGO
GROUP BY DFP.IDDEPOSITO;

CREATE UNIQUE CLUSTERED INDEX CIX_Periodicidades
    ON #Periodicidades (id_deposito);

SET @Filas = (SELECT COUNT(*) FROM #Periodicidades);
INSERT INTO #Metricas (etapa, filas, duracion_ms)
VALUES (
    '3. Periodicidades',
    @Filas,
    DATEDIFF_BIG(millisecond, @InicioEtapa, SYSDATETIME())
);

/* 4. Las bandas se resuelven en conjunto, sin OUTER APPLY por depósito. */
SET @InicioEtapa = SYSDATETIME();

SELECT
    DIP.IDDEPOSITO AS id_deposito,
    MIN(CONCAT('DE ', TI.DIASINICIO, ' A ', TI.DIASFIN)) AS periodo_plazo,
    COUNT_BIG(*) AS coincidencias
INTO #Bandas
FROM INVERSION.DEPOSITO_ITEMPLAZO FOR SYSTEM_TIME AS OF @FechaCierrePlazo AS DIP
INNER JOIN #DepositosCorte AS D
    ON D.id_deposito = DIP.IDDEPOSITO
INNER JOIN INVERSION.DEPOSITO_ITEMPLAZO_TEMPORIZACION
    FOR SYSTEM_TIME AS OF @FechaCierrePlazo AS DIT
    ON DIT.IDDEPOSITOITEMPLAZO = DIP.ID
INNER JOIN INVERSION.TEMPORIZACION_INVERSION AS TI WITH (NOLOCK)
    ON TI.ID = DIT.IDTEMPORIZACION
WHERE DIP.IDITEMPLAZO = 1
GROUP BY DIP.IDDEPOSITO;

CREATE UNIQUE CLUSTERED INDEX CIX_Bandas
    ON #Bandas (id_deposito);

SET @Filas = (SELECT COUNT(*) FROM #Bandas);
INSERT INTO #Metricas (etapa, filas, duracion_ms)
VALUES (
    '4. Bandas de plazo historicas',
    @Filas,
    DATEDIFF_BIG(millisecond, @InicioEtapa, SYSDATETIME())
);

/* 5. Renovaciones restringidas al corte; no es una tabla temporal. */
SET @InicioEtapa = SYSDATETIME();

SELECT
    DR.IDDEPOSITODESTINO AS id_deposito,
    MIN(DR.IDDEPOSITOORIGEN) AS id_deposito_origen,
    COUNT_BIG(*) AS coincidencias
INTO #Renovaciones
FROM INVERSION.DEPOSITO_RENOVACION AS DR WITH (NOLOCK)
INNER JOIN #DepositosCorte AS D
    ON D.id_deposito = DR.IDDEPOSITODESTINO
GROUP BY DR.IDDEPOSITODESTINO;

CREATE UNIQUE CLUSTERED INDEX CIX_Renovaciones
    ON #Renovaciones (id_deposito);

SET @Filas = (SELECT COUNT(*) FROM #Renovaciones);
INSERT INTO #Metricas (etapa, filas, duracion_ms)
VALUES (
    '5. Renovaciones',
    @Filas,
    DATEDIFF_BIG(millisecond, @InicioEtapa, SYSDATETIME())
);

/* 6. Ensamble de dimensiones y controles de integridad. */
SET @InicioEtapa = SYSDATETIME();

SELECT
    COUNT(*) AS filas_resultantes,
    COUNT(DISTINCT D.id_deposito) AS operaciones,
    SUM(D.saldo) AS saldo,
    SUM(CASE WHEN A.ID IS NULL THEN 1 ELSE 0 END) AS sin_agencia,
    SUM(CASE WHEN U.USUARIO IS NULL THEN 1 ELSE 0 END) AS asesor_sin_nombre,
    SUM(CASE WHEN DPC.IDDIVISIONNIVELBAJO IS NULL THEN 1 ELSE 0 END) AS sin_ubicacion,
    SUM(CASE WHEN F.id_deposito IS NULL THEN 1 ELSE 0 END) AS sin_periodicidad,
    SUM(CASE WHEN B.id_deposito IS NULL THEN 1 ELSE 0 END) AS sin_banda_plazo,
    SUM(CASE WHEN B.coincidencias > 1 THEN 1 ELSE 0 END) AS con_multiples_bandas,
    SUM(CASE WHEN R.id_deposito IS NULL THEN 1 ELSE 0 END) AS nuevos,
    SUM(CASE WHEN R.id_deposito IS NOT NULL THEN 1 ELSE 0 END) AS renovados,
    SUM(CASE WHEN PP.id_cliente IS NULL THEN 1 ELSE 0 END) AS sin_prestamo,
    SUM(CASE WHEN PP.id_cliente IS NOT NULL THEN 1 ELSE 0 END) AS con_prestamo
FROM #DepositosCorte AS D
LEFT JOIN GENERAL.AGENCIA AS A WITH (NOLOCK)
    ON A.ID = D.id_agencia
LEFT JOIN SEGURIDAD.USUARIO AS U WITH (NOLOCK)
    ON U.USUARIO = D.codigo_usuario
LEFT JOIN GENERAL.DIVISIONPOLITICA_CONSOLIDADO AS DPC WITH (NOLOCK)
    ON DPC.IDDIVISIONNIVELBAJO = D.id_residencia
LEFT JOIN #Periodicidades AS F
    ON F.id_deposito = D.id_deposito
LEFT JOIN #Bandas AS B
    ON B.id_deposito = D.id_deposito
LEFT JOIN #Renovaciones AS R
    ON R.id_deposito = D.id_deposito
LEFT JOIN #PrestamosPorCliente AS PP
    ON PP.id_cliente = D.id_cliente;

SET @Filas = (SELECT COUNT(*) FROM #DepositosCorte);
INSERT INTO #Metricas (etapa, filas, duracion_ms)
VALUES (
    '6. Ensamble y controles',
    @Filas,
    DATEDIFF_BIG(millisecond, @InicioEtapa, SYSDATETIME())
);

SELECT etapa, filas, duracion_ms
FROM #Metricas
ORDER BY etapa;

SET STATISTICS TIME OFF;
SET STATISTICS IO OFF;

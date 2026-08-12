/*
    Reporte analítico de inversiones a plazo.

    Grano de salida:
      Un registro agregado por corte mensual y por combinación de dimensiones.

    Reglas de negocio:
      - Solo incluye depósitos ACTIVO (A) y EXIGIBLE (E).
      - Una operación es un depósito distinto, no una fila de ítems de interés.
      - CONDICION es RENOVADO cuando existe un origen en DEPOSITO_RENOVACION;
        de lo contrario es NUEVO.
      - TASA_EFECTIVA = TASA + VARIACION_TASA.
      - TASA_ENTERA es la parte entera de la tasa efectiva y TASA_DECIMAL es
        su valor con dos decimales. Ambas columnas permiten construir las dos
        visualizaciones solicitadas sin volver a consultar el origen.

    Historial:
      Para un mes cerrado se consulta DEPOSITO e ítems de plazo con
      FOR SYSTEM_TIME AS OF la fecha de cierre registrada. Si falta tal cierre
      se aborta: nunca se sustituyen datos históricos con datos vigentes.
      El mes actual se lee de las tablas vigentes.

    Nota:
      CODIGOTIPODEPOSITO = '001' se interpreta como PAGO PERIODICO, conforme
      al procedimiento legado. Debe validarse contra el catálogo de negocio si
      aparecen nuevos tipos de depósito.
*/
CREATE OR ALTER PROCEDURE [INVERSION].[REPORTE_ANALITICO_INVERSIONES]
    @PeriodoDesde date,
    @PeriodoHasta date
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @PeriodoDesde IS NULL OR @PeriodoHasta IS NULL
        THROW 50000, 'PeriodoDesde y PeriodoHasta son obligatorios.', 1;

    IF @PeriodoHasta < @PeriodoDesde
        THROW 50001, 'PeriodoHasta no puede ser menor que PeriodoDesde.', 1;

    DECLARE @FechaSistema date = (
        SELECT MAX(CAST(CS.FECHASISTEMA AS date))
        FROM GENERAL.CALENDARIO_SISTEMA AS CS WITH (NOLOCK)
        WHERE CS.SECERRO = 0
    );

    IF @FechaSistema IS NULL
        THROW 50002, 'No se encontró la fecha del sistema abierta.', 1;

    IF @PeriodoHasta > @FechaSistema
        THROW 50003, 'PeriodoHasta no puede ser posterior a la fecha del sistema.', 1;

    DECLARE @MesDesde date = DATEFROMPARTS(YEAR(@PeriodoDesde), MONTH(@PeriodoDesde), 1);
    DECLARE @MesHasta date = DATEFROMPARTS(YEAR(@PeriodoHasta), MONTH(@PeriodoHasta), 1);
    DECLARE @CantidadMeses int = DATEDIFF(month, @MesDesde, @MesHasta) + 1;

    DECLARE @Cortes TABLE (
        FechaCorte date NOT NULL PRIMARY KEY,
        FechaCierrePlazo datetime NULL,
        FechaCierreColocacion datetime NULL
    );

    /*
       Cada mes se corta en la última fecha operativa disponible. Para el mes
       actual el corte será exactamente la fecha del sistema.
    */
    ;WITH Meses AS (
        SELECT @MesDesde AS Mes
        UNION ALL
        SELECT DATEADD(month, 1, Mes)
        FROM Meses
        WHERE Mes < @MesHasta
    )
    INSERT INTO @Cortes (FechaCorte, FechaCierrePlazo, FechaCierreColocacion)
    SELECT
        Corte.FechaCorte,
        Cierre.FECHACIERREPLAZO,
        Cierre.FECHACIERRECOLOCACION
    FROM Meses AS M
    CROSS APPLY (
        SELECT TOP (1) CAST(CS.FECHASISTEMA AS date) AS FechaCorte
        FROM GENERAL.CALENDARIO_SISTEMA AS CS WITH (NOLOCK)
        WHERE CAST(CS.FECHASISTEMA AS date) >= M.Mes
          AND CAST(CS.FECHASISTEMA AS date) <=
                CASE WHEN EOMONTH(M.Mes) > @FechaSistema THEN @FechaSistema ELSE EOMONTH(M.Mes) END
        ORDER BY CS.FECHASISTEMA DESC
    ) AS Corte
    LEFT JOIN GENERAL.EMPRESA_CIERREHISTORICO AS Cierre WITH (NOLOCK)
        ON CAST(Cierre.FECHASISTEMA AS date) = Corte.FechaCorte
    OPTION (MAXRECURSION 1200);

    IF (SELECT COUNT(*) FROM @Cortes) <> @CantidadMeses
        THROW 50004, 'No existe una fecha operativa para uno o más meses del rango solicitado.', 1;

    IF EXISTS (
        SELECT 1
        FROM @Cortes
        WHERE FechaCorte < @FechaSistema
          AND (FechaCierrePlazo IS NULL OR FechaCierreColocacion IS NULL)
    )
        THROW 50005, 'Falta el cierre histórico de plazo o colocación para uno o más cortes solicitados.', 1;

    CREATE TABLE #PrestamosPorCliente (
        IdCliente int NOT NULL PRIMARY KEY,
        SaldoPrestamo decimal(18, 2) NOT NULL
    );

    CREATE TABLE #HechosInversion (
        FechaCorte date NOT NULL,
        IdDeposito int NOT NULL,
        Agencia nvarchar(150) NOT NULL,
        Asesor nvarchar(150) NOT NULL,
        PeriodicidadPago nvarchar(150) NOT NULL,
        TipoPago nvarchar(20) NOT NULL,
        Condicion nvarchar(20) NOT NULL,
        Periodo nvarchar(50) NOT NULL,
        Estado nvarchar(20) NOT NULL,
        Provincia nvarchar(150) NOT NULL,
        Canton nvarchar(150) NOT NULL,
        Parroquia nvarchar(150) NOT NULL,
        TienePrestamo nvarchar(2) NOT NULL,
        TasaEfectiva decimal(18, 4) NOT NULL,
        TasaEntera int NOT NULL,
        TasaDecimal decimal(18, 2) NOT NULL,
        Saldo decimal(18, 2) NOT NULL,
        PRIMARY KEY (FechaCorte, IdDeposito)
    );

    DECLARE
        @FechaCorte date,
        @FechaCierrePlazo datetime,
        @FechaCierreColocacion datetime;

    DECLARE CursorCortes CURSOR LOCAL FAST_FORWARD FOR
        SELECT FechaCorte, FechaCierrePlazo, FechaCierreColocacion
        FROM @Cortes
        ORDER BY FechaCorte;

    OPEN CursorCortes;
    FETCH NEXT FROM CursorCortes
        INTO @FechaCorte, @FechaCierrePlazo, @FechaCierreColocacion;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        TRUNCATE TABLE #PrestamosPorCliente;

        IF @FechaCorte = @FechaSistema
        BEGIN
            INSERT INTO #PrestamosPorCliente (IdCliente, SaldoPrestamo)
            SELECT PC.IDCLIENTE, SUM(P.SALDO)
            FROM COLOCACION.PRESTAMO AS P WITH (NOLOCK)
            INNER JOIN COLOCACION.PRESTAMO_CLIENTE AS PC WITH (NOLOCK)
                ON PC.IDPRESTAMO = P.ID
               AND PC.ACTIVO = 1
            WHERE P.CODIGOESTADO <> 'C'
            GROUP BY PC.IDCLIENTE;

            INSERT INTO #HechosInversion (
                FechaCorte, IdDeposito, Agencia, Asesor, PeriodicidadPago,
                TipoPago, Condicion, Periodo, Estado, Provincia, Canton,
                Parroquia, TienePrestamo, TasaEfectiva, TasaEntera,
                TasaDecimal, Saldo
            )
            SELECT
                @FechaCorte,
                D.ID,
                COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), ''), 'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), ''), D.CODIGOUSUARIO, 'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(Frecuencia.PERIODICIDADPAGO)), ''), 'SIN DATOS'),
                CASE WHEN D.CODIGOTIPODEPOSITO = '001' THEN 'PERIODICO' ELSE 'VENCIMIENTO' END,
                CASE WHEN Renovacion.IDDEPOSITOORIGEN IS NULL THEN 'NUEVO' ELSE 'RENOVADO' END,
                COALESCE(Banda.PERIODO, 'SIN DATOS'),
                CASE D.CODIGOESTADODEPOSITO WHEN 'A' THEN 'ACTIVO' WHEN 'E' THEN 'EXIGIBLE' END,
                COALESCE(NULLIF(LTRIM(RTRIM(DPC.PROVINCIA)), ''), 'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(DPC.CANTON)), ''), 'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(DPC.PARROQUIA)), ''), 'SIN DATOS'),
                CASE WHEN Prestamo.IdCliente IS NULL THEN 'NO' ELSE 'SI' END,
                Tasa.TASA_EFECTIVA,
                CONVERT(int, FLOOR(Tasa.TASA_EFECTIVA)),
                CONVERT(decimal(18, 2), Tasa.TASA_EFECTIVA),
                D.MONTO
            FROM INVERSION.DEPOSITO AS D WITH (NOLOCK)
            INNER JOIN INVERSION.DEPOSITO_CLIENTE AS DC WITH (NOLOCK)
                ON DC.IDDEPOSITO = D.ID
               AND DC.ESPRINCIPAL = 1
               AND DC.ACTIVO = 1
            INNER JOIN CLIENTES.CLIENTE AS C WITH (NOLOCK)
                ON C.ID = DC.IDCLIENTE
            INNER JOIN SUJETO.PERSONA AS Persona WITH (NOLOCK)
                ON Persona.ID = C.IDPERSONA
            LEFT JOIN GENERAL.AGENCIA AS A WITH (NOLOCK)
                ON A.ID = D.IDAGENCIA
            LEFT JOIN SEGURIDAD.USUARIO AS U WITH (NOLOCK)
                ON U.USUARIO = D.CODIGOUSUARIO
            LEFT JOIN GENERAL.DIVISIONPOLITICA_CONSOLIDADO AS DPC WITH (NOLOCK)
                ON DPC.IDDIVISIONNIVELBAJO = Persona.IDRESIDENCIA
            LEFT JOIN #PrestamosPorCliente AS Prestamo
                ON Prestamo.IdCliente = C.ID
            OUTER APPLY (
                SELECT TOP (1) FP.NOMBRE AS PERIODICIDADPAGO
                FROM INVERSION.DEPOSITO_FRECUENCIA_PAGO AS DFP WITH (NOLOCK)
                INNER JOIN INVERSION.FRECUENCIA_PAGO AS FP WITH (NOLOCK)
                    ON FP.CODIGO = DFP.CODIGOFRECUENCIAPAGO
                WHERE DFP.IDDEPOSITO = D.ID
                ORDER BY DFP.CODIGOFRECUENCIAPAGO
            ) AS Frecuencia
            OUTER APPLY (
                SELECT TOP (1)
                    CONCAT('DE ', TI.DIASINICIO, ' A ', TI.DIASFIN) AS PERIODO
                FROM INVERSION.DEPOSITO_ITEMPLAZO AS DIP WITH (NOLOCK)
                INNER JOIN INVERSION.DEPOSITO_ITEMPLAZO_TEMPORIZACION AS DIT WITH (NOLOCK)
                    ON DIT.IDDEPOSITOITEMPLAZO = DIP.ID
                INNER JOIN INVERSION.TEMPORIZACION_INVERSION AS TI WITH (NOLOCK)
                    ON TI.ID = DIT.IDTEMPORIZACION
                WHERE DIP.IDDEPOSITO = D.ID
                  AND DIP.IDITEMPLAZO = 1
                ORDER BY TI.DIASINICIO, TI.DIASFIN
            ) AS Banda
            OUTER APPLY (
                SELECT TOP (1) DR.IDDEPOSITOORIGEN
                FROM INVERSION.DEPOSITO_RENOVACION AS DR WITH (NOLOCK)
                WHERE DR.IDDEPOSITODESTINO = D.ID
                ORDER BY DR.IDDEPOSITOORIGEN
            ) AS Renovacion
            CROSS APPLY (
                SELECT CONVERT(decimal(18, 4), COALESCE(D.TASA, 0) + COALESCE(D.VARIACION_TASA, 0)) AS TASA_EFECTIVA
            ) AS Tasa
            WHERE D.CODIGOESTADODEPOSITO IN ('A', 'E');
        END
        ELSE
        BEGIN
            INSERT INTO #PrestamosPorCliente (IdCliente, SaldoPrestamo)
            SELECT PC.IDCLIENTE, SUM(P.SALDO)
            FROM COLOCACION.PRESTAMO FOR SYSTEM_TIME AS OF @FechaCierreColocacion AS P WITH (NOLOCK)
            INNER JOIN COLOCACION.PRESTAMO_CLIENTE AS PC WITH (NOLOCK)
                ON PC.IDPRESTAMO = P.ID
               AND PC.ACTIVO = 1
            WHERE P.CODIGOESTADO <> 'C'
            GROUP BY PC.IDCLIENTE;

            INSERT INTO #HechosInversion (
                FechaCorte, IdDeposito, Agencia, Asesor, PeriodicidadPago,
                TipoPago, Condicion, Periodo, Estado, Provincia, Canton,
                Parroquia, TienePrestamo, TasaEfectiva, TasaEntera,
                TasaDecimal, Saldo
            )
            SELECT
                @FechaCorte,
                D.ID,
                COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), ''), 'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), ''), D.CODIGOUSUARIO, 'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(Frecuencia.PERIODICIDADPAGO)), ''), 'SIN DATOS'),
                CASE WHEN D.CODIGOTIPODEPOSITO = '001' THEN 'PERIODICO' ELSE 'VENCIMIENTO' END,
                CASE WHEN Renovacion.IDDEPOSITOORIGEN IS NULL THEN 'NUEVO' ELSE 'RENOVADO' END,
                COALESCE(Banda.PERIODO, 'SIN DATOS'),
                CASE D.CODIGOESTADODEPOSITO WHEN 'A' THEN 'ACTIVO' WHEN 'E' THEN 'EXIGIBLE' END,
                COALESCE(NULLIF(LTRIM(RTRIM(DPC.PROVINCIA)), ''), 'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(DPC.CANTON)), ''), 'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(DPC.PARROQUIA)), ''), 'SIN DATOS'),
                CASE WHEN Prestamo.IdCliente IS NULL THEN 'NO' ELSE 'SI' END,
                Tasa.TASA_EFECTIVA,
                CONVERT(int, FLOOR(Tasa.TASA_EFECTIVA)),
                CONVERT(decimal(18, 2), Tasa.TASA_EFECTIVA),
                D.MONTO
            FROM INVERSION.DEPOSITO FOR SYSTEM_TIME AS OF @FechaCierrePlazo AS D WITH (NOLOCK)
            INNER JOIN INVERSION.DEPOSITO_CLIENTE AS DC WITH (NOLOCK)
                ON DC.IDDEPOSITO = D.ID
               AND DC.ESPRINCIPAL = 1
               AND DC.ACTIVO = 1
            INNER JOIN CLIENTES.CLIENTE AS C WITH (NOLOCK)
                ON C.ID = DC.IDCLIENTE
            INNER JOIN SUJETO.PERSONA AS Persona WITH (NOLOCK)
                ON Persona.ID = C.IDPERSONA
            LEFT JOIN GENERAL.AGENCIA AS A WITH (NOLOCK)
                ON A.ID = D.IDAGENCIA
            LEFT JOIN SEGURIDAD.USUARIO AS U WITH (NOLOCK)
                ON U.USUARIO = D.CODIGOUSUARIO
            LEFT JOIN GENERAL.DIVISIONPOLITICA_CONSOLIDADO AS DPC WITH (NOLOCK)
                ON DPC.IDDIVISIONNIVELBAJO = Persona.IDRESIDENCIA
            LEFT JOIN #PrestamosPorCliente AS Prestamo
                ON Prestamo.IdCliente = C.ID
            OUTER APPLY (
                SELECT TOP (1) FP.NOMBRE AS PERIODICIDADPAGO
                FROM INVERSION.DEPOSITO_FRECUENCIA_PAGO AS DFP WITH (NOLOCK)
                INNER JOIN INVERSION.FRECUENCIA_PAGO AS FP WITH (NOLOCK)
                    ON FP.CODIGO = DFP.CODIGOFRECUENCIAPAGO
                WHERE DFP.IDDEPOSITO = D.ID
                ORDER BY DFP.CODIGOFRECUENCIAPAGO
            ) AS Frecuencia
            OUTER APPLY (
                SELECT TOP (1)
                    CONCAT('DE ', TI.DIASINICIO, ' A ', TI.DIASFIN) AS PERIODO
                FROM INVERSION.DEPOSITO_ITEMPLAZO FOR SYSTEM_TIME AS OF @FechaCierrePlazo AS DIP WITH (NOLOCK)
                INNER JOIN INVERSION.DEPOSITO_ITEMPLAZO_TEMPORIZACION FOR SYSTEM_TIME AS OF @FechaCierrePlazo AS DIT WITH (NOLOCK)
                    ON DIT.IDDEPOSITOITEMPLAZO = DIP.ID
                INNER JOIN INVERSION.TEMPORIZACION_INVERSION AS TI WITH (NOLOCK)
                    ON TI.ID = DIT.IDTEMPORIZACION
                WHERE DIP.IDDEPOSITO = D.ID
                  AND DIP.IDITEMPLAZO = 1
                ORDER BY TI.DIASINICIO, TI.DIASFIN
            ) AS Banda
            OUTER APPLY (
                SELECT TOP (1) DR.IDDEPOSITOORIGEN
                FROM INVERSION.DEPOSITO_RENOVACION AS DR WITH (NOLOCK)
                WHERE DR.IDDEPOSITODESTINO = D.ID
                ORDER BY DR.IDDEPOSITOORIGEN
            ) AS Renovacion
            CROSS APPLY (
                SELECT CONVERT(decimal(18, 4), COALESCE(D.TASA, 0) + COALESCE(D.VARIACION_TASA, 0)) AS TASA_EFECTIVA
            ) AS Tasa
            WHERE D.CODIGOESTADODEPOSITO IN ('A', 'E');
        END;

        FETCH NEXT FROM CursorCortes
            INTO @FechaCorte, @FechaCierrePlazo, @FechaCierreColocacion;
    END;

    CLOSE CursorCortes;
    DEALLOCATE CursorCortes;

    SELECT
        H.FechaCorte AS fecha_corte,
        CONVERT(char(7), H.FechaCorte, 120) AS periodo,
        YEAR(H.FechaCorte) AS anio,
        MONTH(H.FechaCorte) AS mes,
        H.Agencia AS agencia,
        H.Asesor AS asesor,
        H.PeriodicidadPago AS periodicidad_pago,
        H.TipoPago AS tipo_pago,
        H.Condicion AS condicion,
        H.Periodo AS periodo_plazo,
        H.Estado AS estado,
        H.Provincia AS provincia,
        H.Canton AS canton,
        H.Parroquia AS parroquia,
        H.TienePrestamo AS tiene_prestamo,
        H.TasaEfectiva AS tasa_efectiva,
        H.TasaEntera AS tasa_entera,
        H.TasaDecimal AS tasa_decimal,
        COUNT(DISTINCT H.IdDeposito) AS operaciones,
        SUM(H.Saldo) AS saldo
    FROM #HechosInversion AS H
    GROUP BY
        H.FechaCorte, H.Agencia, H.Asesor, H.PeriodicidadPago, H.TipoPago,
        H.Condicion, H.Periodo, H.Estado, H.Provincia, H.Canton, H.Parroquia,
        H.TienePrestamo, H.TasaEfectiva, H.TasaEntera, H.TasaDecimal
    ORDER BY
        H.FechaCorte, H.Agencia, H.Asesor, H.PeriodicidadPago, H.TipoPago,
        H.Condicion, H.Periodo, H.Estado, H.Provincia, H.Canton, H.Parroquia,
        H.TienePrestamo, H.TasaEfectiva;
END;
GO

/*
EXEC INVERSION.REPORTE_ANALITICO_INVERSIONES
    @PeriodoDesde = '2026-01-01',
    @PeriodoHasta = '2026-07-30';
*/

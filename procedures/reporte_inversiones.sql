/*
    Reemplazo optimizado de INVERSION.REPORTE_PBI_BANDAS_INVERSIONES.

    Devuelve una fotografía mensual agregada de depósitos ACTIVO y EXIGIBLE.
    Cada corte usa las tablas temporales de inversiones y colocación; las
    relaciones no temporales se usan únicamente para las dimensiones vigentes.

    Si no se indican fechas, usa el primer mes con cierres completos:
    2019-09-01 hasta la fecha abierta del sistema.
*/
CREATE OR ALTER PROCEDURE [INVERSION].[REPORTE_ANALITICO_INVERSIONES]
    @FechaDesde date = '2019-09-01',
    @FechaHasta date = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @FechaSistema date = (
        SELECT MAX(CAST(CS.FECHASISTEMA AS date))
        FROM GENERAL.CALENDARIO_SISTEMA AS CS WITH (NOLOCK)
        WHERE CS.SECERRO = 0
          /* El calendario puede contener fechas futuras preparadas (p. ej. 2099). */
          AND CAST(CS.FECHASISTEMA AS date) <= CAST(GETDATE() AS date)
    );

    IF @FechaSistema IS NULL
        THROW 50000, 'No se encontró una fecha del sistema abierta.', 1;

    SET @FechaHasta = COALESCE(@FechaHasta, @FechaSistema);

    IF @FechaDesde IS NULL OR @FechaHasta IS NULL
        THROW 50001, 'FechaDesde y FechaHasta son obligatorias.', 1;

    IF @FechaHasta < @FechaDesde
        THROW 50002, 'FechaHasta no puede ser menor que FechaDesde.', 1;

    IF @FechaHasta > @FechaSistema
        THROW 50003, 'FechaHasta no puede superar la fecha del sistema.', 1;

    DECLARE @MesDesde date = DATEFROMPARTS(YEAR(@FechaDesde), MONTH(@FechaDesde), 1);
    DECLARE @MesHasta date = DATEFROMPARTS(YEAR(@FechaHasta), MONTH(@FechaHasta), 1);
    DECLARE @CantidadMeses int = DATEDIFF(month, @MesDesde, @MesHasta) + 1;

    DECLARE @Cortes TABLE (
        FechaCorte date NOT NULL PRIMARY KEY,
        FechaCierrePlazo datetime NULL,
        FechaCierreColocacion datetime NULL
    );

    /*
       Estos dos fines de mes no tienen cierres completos. Se omiten porque el
       último cierre disponible está a 12 y 3 días, respectivamente, y no
       representa una fotografía mensual confiable.
    */
    DECLARE @CortesOmitidos TABLE (
        FechaCorte date NOT NULL PRIMARY KEY
    );
    INSERT INTO @CortesOmitidos (FechaCorte)
    VALUES ('2019-07-31'), ('2019-08-31');

    /* Último día operativo disponible para cada mes solicitado. */
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
              CASE
                  WHEN EOMONTH(M.Mes) > @FechaHasta THEN @FechaHasta
                  ELSE EOMONTH(M.Mes)
              END
        ORDER BY CS.FECHASISTEMA DESC
    ) AS Corte
    LEFT JOIN GENERAL.EMPRESA_CIERREHISTORICO AS Cierre WITH (NOLOCK)
        ON CAST(Cierre.FECHASISTEMA AS date) = Corte.FechaCorte
    OPTION (MAXRECURSION 1200);

    IF (SELECT COUNT(*) FROM @Cortes) <> @CantidadMeses
        THROW 50004, 'No existe una fecha operativa para uno o más meses solicitados.', 1;

    DELETE C
    FROM @Cortes AS C
    INNER JOIN @CortesOmitidos AS O
        ON O.FechaCorte = C.FechaCorte;

    /* Nunca se sustituyen cortes históricos con datos vigentes. */
    IF EXISTS (
        SELECT 1
        FROM @Cortes
        WHERE FechaCorte < @FechaSistema
          AND (FechaCierrePlazo IS NULL OR FechaCierreColocacion IS NULL)
    )
        THROW 50005, 'Falta el cierre de plazo o colocación para uno o más cortes históricos.', 1;

    CREATE TABLE #DepositosCorte (
        id_deposito int NOT NULL PRIMARY KEY CLUSTERED,
        saldo decimal(18, 2) NOT NULL,
        id_agencia int NULL,
        codigo_usuario nvarchar(100) NULL,
        codigo_tipo_deposito nvarchar(20) NULL,
        codigo_estado_deposito nvarchar(10) NOT NULL,
        pago_periodico_interes bit NOT NULL,
        tasa_normal decimal(18, 2) NOT NULL,
        tasa_variacion decimal(18, 2) NOT NULL,
        plazo_dias int NOT NULL,
        id_cliente int NOT NULL,
        id_residencia int NULL
    );
    CREATE INDEX IX_DepositosCorte_Cliente ON #DepositosCorte (id_cliente);

    CREATE TABLE #ClientesCorte (
        id_cliente int NOT NULL PRIMARY KEY CLUSTERED
    );

    CREATE TABLE #PrestamosPorCliente (
        id_cliente int NOT NULL PRIMARY KEY CLUSTERED,
        saldo_prestamo decimal(28, 2) NOT NULL
    );

    CREATE TABLE #Periodicidades (
        id_deposito int NOT NULL PRIMARY KEY CLUSTERED,
        periodicidad_pago nvarchar(150) NULL
    );

    CREATE TABLE #Bandas (
        id_deposito int NOT NULL PRIMARY KEY CLUSTERED,
        periodo_plazo nvarchar(50) NULL,
        coincidencias bigint NOT NULL
    );

    CREATE TABLE #Renovaciones (
        id_deposito int NOT NULL PRIMARY KEY CLUSTERED,
        id_deposito_origen int NOT NULL,
        coincidencias bigint NOT NULL
    );

    CREATE TABLE #Resultado (
        fecha_corte date NOT NULL,
        periodo char(7) NOT NULL,
        anio int NOT NULL,
        mes int NOT NULL,
        agencia nvarchar(150) NOT NULL,
        asesor nvarchar(150) NOT NULL,
        periodicidad_pago nvarchar(150) NOT NULL,
        tipo_pago nvarchar(20) NOT NULL,
        condicion nvarchar(20) NOT NULL,
        periodo_plazo nvarchar(50) NOT NULL,
        plazo_dias int NOT NULL,
        estado nvarchar(20) NOT NULL,
        provincia nvarchar(150) NOT NULL,
        canton nvarchar(150) NOT NULL,
        parroquia nvarchar(150) NOT NULL,
        tiene_prestamo bit NOT NULL,
        tasa_efectiva decimal(18, 4) NOT NULL,
        tasa_entera int NOT NULL,
        tasa_decimal decimal(18, 2) NOT NULL,
        operaciones int NOT NULL,
        saldo decimal(28, 2) NOT NULL
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
        TRUNCATE TABLE #DepositosCorte;
        TRUNCATE TABLE #ClientesCorte;
        TRUNCATE TABLE #PrestamosPorCliente;
        TRUNCATE TABLE #Periodicidades;
        TRUNCATE TABLE #Bandas;
        TRUNCATE TABLE #Renovaciones;

        /* Una sola lectura de depósitos para el corte actual o histórico. */
        IF @FechaCorte = @FechaSistema
        BEGIN
            INSERT INTO #DepositosCorte (
                id_deposito, saldo, id_agencia, codigo_usuario,
                codigo_tipo_deposito, codigo_estado_deposito, pago_periodico_interes,
                tasa_normal, tasa_variacion, plazo_dias, id_cliente, id_residencia
            )
            SELECT
                D.ID,
                D.MONTO,
                D.IDAGENCIA,
                D.CODIGOUSUARIO,
                D.CODIGOTIPODEPOSITO,
                D.CODIGOESTADODEPOSITO,
                D.PAGOPERIODICOINTERES,
                D.TASA,
                D.VARIACION_TASA,
                D.PLAZO,
                C.ID,
                Persona.IDRESIDENCIA
            FROM INVERSION.DEPOSITO AS D WITH (NOLOCK)
            INNER JOIN INVERSION.DEPOSITO_CLIENTE AS DC WITH (NOLOCK)
                ON DC.IDDEPOSITO = D.ID
               AND DC.ESPRINCIPAL = 1
               AND DC.ACTIVO = 1
            INNER JOIN CLIENTES.CLIENTE AS C WITH (NOLOCK)
                ON C.ID = DC.IDCLIENTE
            INNER JOIN SUJETO.PERSONA AS Persona WITH (NOLOCK)
                ON Persona.ID = C.IDPERSONA
            WHERE D.CODIGOESTADODEPOSITO IN ('A', 'E');
        END
        ELSE
        BEGIN
            INSERT INTO #DepositosCorte (
                id_deposito, saldo, id_agencia, codigo_usuario,
                codigo_tipo_deposito, codigo_estado_deposito, pago_periodico_interes,
                tasa_normal, tasa_variacion, plazo_dias, id_cliente, id_residencia
            )
            SELECT
                D.ID,
                D.MONTO,
                D.IDAGENCIA,
                D.CODIGOUSUARIO,
                D.CODIGOTIPODEPOSITO,
                D.CODIGOESTADODEPOSITO,
                D.PAGOPERIODICOINTERES,
                D.TASA,
                D.VARIACION_TASA,
                D.PLAZO,
                C.ID,
                Persona.IDRESIDENCIA
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
        END;

        INSERT INTO #ClientesCorte (id_cliente)
        SELECT DISTINCT id_cliente
        FROM #DepositosCorte;

        /* Una sola lectura de préstamos, restringida a clientes del corte. */
        IF @FechaCorte = @FechaSistema
        BEGIN
            INSERT INTO #PrestamosPorCliente (id_cliente, saldo_prestamo)
            SELECT PC.IDCLIENTE, CONVERT(decimal(28, 2), SUM(P.SALDO))
            FROM COLOCACION.PRESTAMO AS P WITH (NOLOCK)
            INNER JOIN COLOCACION.PRESTAMO_CLIENTE AS PC WITH (NOLOCK)
                ON PC.IDPRESTAMO = P.ID
               AND PC.ACTIVO = 1
            INNER JOIN #ClientesCorte AS CC
                ON CC.id_cliente = PC.IDCLIENTE
            WHERE P.CODIGOESTADO <> 'C'
            GROUP BY PC.IDCLIENTE;
        END
        ELSE
        BEGIN
            INSERT INTO #PrestamosPorCliente (id_cliente, saldo_prestamo)
            SELECT PC.IDCLIENTE, CONVERT(decimal(28, 2), SUM(P.SALDO))
            FROM COLOCACION.PRESTAMO FOR SYSTEM_TIME AS OF @FechaCierreColocacion AS P
            INNER JOIN COLOCACION.PRESTAMO_CLIENTE AS PC WITH (NOLOCK)
                ON PC.IDPRESTAMO = P.ID
               AND PC.ACTIVO = 1
            INNER JOIN #ClientesCorte AS CC
                ON CC.id_cliente = PC.IDCLIENTE
            WHERE P.CODIGOESTADO <> 'C'
            GROUP BY PC.IDCLIENTE;
        END;

        INSERT INTO #Periodicidades (id_deposito, periodicidad_pago)
        SELECT
            DFP.IDDEPOSITO,
            MAX(FP.NOMBRE)
        FROM INVERSION.DEPOSITO_FRECUENCIA_PAGO AS DFP WITH (NOLOCK)
        INNER JOIN #DepositosCorte AS D
            ON D.id_deposito = DFP.IDDEPOSITO
        INNER JOIN INVERSION.FRECUENCIA_PAGO AS FP WITH (NOLOCK)
            ON FP.CODIGO = DFP.CODIGOFRECUENCIAPAGO
        GROUP BY DFP.IDDEPOSITO;

        /* Bandas históricas obtenidas en conjunto; evita APPLY por depósito. */
        IF @FechaCorte = @FechaSistema
        BEGIN
            INSERT INTO #Bandas (id_deposito, periodo_plazo, coincidencias)
            SELECT
                DIP.IDDEPOSITO,
                MIN(CONCAT('DE ', TI.DIASINICIO, ' A ', TI.DIASFIN)),
                COUNT_BIG(*)
            FROM INVERSION.DEPOSITO_ITEMPLAZO AS DIP WITH (NOLOCK)
            INNER JOIN #DepositosCorte AS D
                ON D.id_deposito = DIP.IDDEPOSITO
            INNER JOIN INVERSION.DEPOSITO_ITEMPLAZO_TEMPORIZACION AS DIT WITH (NOLOCK)
                ON DIT.IDDEPOSITOITEMPLAZO = DIP.ID
            INNER JOIN INVERSION.TEMPORIZACION_INVERSION AS TI WITH (NOLOCK)
                ON TI.ID = DIT.IDTEMPORIZACION
            WHERE DIP.IDITEMPLAZO = 1
            GROUP BY DIP.IDDEPOSITO;
        END
        ELSE
        BEGIN
            INSERT INTO #Bandas (id_deposito, periodo_plazo, coincidencias)
            SELECT
                DIP.IDDEPOSITO,
                MIN(CONCAT('DE ', TI.DIASINICIO, ' A ', TI.DIASFIN)),
                COUNT_BIG(*)
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
        END;

        INSERT INTO #Renovaciones (id_deposito, id_deposito_origen, coincidencias)
        SELECT
            DR.IDDEPOSITODESTINO,
            MIN(DR.IDDEPOSITOORIGEN),
            COUNT_BIG(*)
        FROM INVERSION.DEPOSITO_RENOVACION AS DR WITH (NOLOCK)
        INNER JOIN #DepositosCorte AS D
            ON D.id_deposito = DR.IDDEPOSITODESTINO
        GROUP BY DR.IDDEPOSITODESTINO;

        INSERT INTO #Resultado (
            fecha_corte, periodo, anio, mes, agencia, asesor,
            periodicidad_pago, tipo_pago, condicion, periodo_plazo, plazo_dias,
            estado,
            provincia, canton, parroquia, tiene_prestamo, tasa_efectiva,
            tasa_entera, tasa_decimal, operaciones, saldo
        )
        SELECT
            @FechaCorte,
            CONVERT(char(7), @FechaCorte, 120),
            YEAR(@FechaCorte),
            MONTH(@FechaCorte),
            COALESCE(NULLIF(LTRIM(RTRIM(A.NOMBRE)), ''), 'SIN DATOS'),
            COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), ''), NULLIF(LTRIM(RTRIM(D.codigo_usuario)), ''), 'SIN DATOS'),
            CASE
                WHEN D.pago_periodico_interes = 0 THEN 'AL VENCIMIENTO'
                ELSE COALESCE(NULLIF(LTRIM(RTRIM(F.periodicidad_pago)), ''), 'SIN DATOS')
            END,
            CASE WHEN D.codigo_tipo_deposito = '001' THEN 'PERIODICO' ELSE 'VENCIMIENTO' END,
            CASE WHEN R.id_deposito IS NULL THEN 'NUEVO' ELSE 'RENOVADO' END,
            COALESCE(B.periodo_plazo, 'SIN DATOS'),
            D.plazo_dias,
            CASE D.codigo_estado_deposito WHEN 'A' THEN 'ACTIVO' WHEN 'E' THEN 'EXIGIBLE' END,
            COALESCE(NULLIF(LTRIM(RTRIM(DPC.PROVINCIA)), ''), 'SIN DATOS'),
            COALESCE(NULLIF(LTRIM(RTRIM(DPC.CANTON)), ''), 'SIN DATOS'),
            COALESCE(NULLIF(LTRIM(RTRIM(DPC.PARROQUIA)), ''), 'SIN DATOS'),
            CONVERT(bit, CASE WHEN PP.id_cliente IS NULL THEN 0 ELSE 1 END),
            Tasa.tasa_efectiva,
            CONVERT(int, FLOOR(Tasa.tasa_efectiva)),
            CONVERT(decimal(18, 2), Tasa.tasa_efectiva),
            COUNT(*),
            CONVERT(decimal(28, 2), SUM(D.saldo))
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
            ON PP.id_cliente = D.id_cliente
        CROSS APPLY (
            SELECT CONVERT(decimal(18, 4), D.tasa_normal + D.tasa_variacion) AS tasa_efectiva
        ) AS Tasa
        GROUP BY
            A.NOMBRE, U.NOMBRE, D.codigo_usuario, D.pago_periodico_interes, F.periodicidad_pago,
            D.codigo_tipo_deposito, R.id_deposito, B.periodo_plazo,
            D.plazo_dias, D.codigo_estado_deposito, DPC.PROVINCIA, DPC.CANTON, DPC.PARROQUIA,
            PP.id_cliente, Tasa.tasa_efectiva;

        FETCH NEXT FROM CursorCortes
            INTO @FechaCorte, @FechaCierrePlazo, @FechaCierreColocacion;
    END;

    CLOSE CursorCortes;
    DEALLOCATE CursorCortes;

    SELECT
        fecha_corte,
        periodo,
        anio,
        mes,
        agencia,
        asesor,
        periodicidad_pago,
        tipo_pago,
        condicion,
        periodo_plazo,
        plazo_dias,
        estado,
        provincia,
        canton,
        parroquia,
        tiene_prestamo,
        tasa_efectiva,
        tasa_entera,
        tasa_decimal,
        operaciones,
        saldo
    FROM #Resultado
    ORDER BY
        fecha_corte,
        agencia,
        asesor,
        periodicidad_pago,
        tipo_pago,
        condicion,
        periodo_plazo,
        plazo_dias,
        estado,
        provincia,
        canton,
        parroquia,
        tiene_prestamo,
        tasa_efectiva;
END;
GO

/*
EXEC INVERSION.REPORTE_PBI_BANDAS_INVERSIONES
    @FechaDesde = '2026-07-01',
    @FechaHasta = '2026-07-29';
*/

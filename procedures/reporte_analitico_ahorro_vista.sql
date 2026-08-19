/*
    Reporte analítico de saldos de ahorros a la vista.

    Grano interno: una cuenta por corte mensual.
    Grano de salida: corte mensual y combinación de dimensiones de análisis.

    Los cortes históricos se reconstruyen con FECHACIERREVISTA para saldos y
    tasas, y con FECHACIERRECOLOCACION para préstamos. No se reemplazan datos
    históricos con datos vigentes cuando falta alguno de esos cierres.
*/
CREATE OR ALTER PROCEDURE [AHORROS].[REPORTE_ANALITICO_AHORROS_VISTA]
    @FechaInicio date,
    @FechaFin date,
    @EsProgramado bit = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50000, 'FechaInicio y FechaFin son obligatorios.', 1;

    IF @FechaFin < @FechaInicio
        THROW 50001, 'FechaFin no puede ser menor que FechaInicio.', 1;

    /*
       El calendario contiene días abiertos futuros. La fecha operativa es el
       primer día posterior al último cierre, no el máximo de SECERRO = 0.
    */
    DECLARE @UltimaFechaCerrada date = (
        SELECT MAX(CAST(CS.FECHASISTEMA AS date))
        FROM GENERAL.CALENDARIO_SISTEMA AS CS
        WHERE CS.SECERRO = 1
    );

    DECLARE @FechaSistema date = (
        SELECT TOP (1) CAST(CS.FECHASISTEMA AS date)
        FROM GENERAL.CALENDARIO_SISTEMA AS CS
        WHERE CAST(CS.FECHASISTEMA AS date) > @UltimaFechaCerrada
        ORDER BY CS.FECHASISTEMA
    );

    IF @FechaSistema IS NULL
        THROW 50002, 'No se encontró la fecha del sistema abierta.', 1;

    IF @FechaFin > @FechaSistema
        THROW 50003, 'FechaFin no puede ser posterior a la fecha del sistema.', 1;

    DECLARE @MesDesde date = DATEFROMPARTS(YEAR(@FechaInicio), MONTH(@FechaInicio), 1);
    DECLARE @MesHasta date = DATEFROMPARTS(YEAR(@FechaFin), MONTH(@FechaFin), 1);
    DECLARE @CantidadMeses int = DATEDIFF(month, @MesDesde, @MesHasta) + 1;

    DECLARE @Cortes TABLE (
        FechaCorte date NOT NULL PRIMARY KEY,
        FechaCierreVista datetime NULL,
        FechaCierreColocacion datetime NULL
    );

    ;WITH Meses AS (
        SELECT @MesDesde AS Mes
        UNION ALL
        SELECT DATEADD(month, 1, Mes)
        FROM Meses
        WHERE Mes < @MesHasta
    )
    INSERT INTO @Cortes (FechaCorte, FechaCierreVista, FechaCierreColocacion)
    SELECT
        Corte.FechaCorte,
        Cierre.FECHACIERREVISTA,
        Cierre.FECHACIERRECOLOCACION
    FROM Meses AS M
    CROSS APPLY (
        SELECT TOP (1) CAST(CS.FECHASISTEMA AS date) AS FechaCorte
        FROM GENERAL.CALENDARIO_SISTEMA AS CS
        WHERE CAST(CS.FECHASISTEMA AS date) >= M.Mes
          AND CAST(CS.FECHASISTEMA AS date) <=
              CASE WHEN EOMONTH(M.Mes) > @FechaSistema THEN @FechaSistema ELSE EOMONTH(M.Mes) END
        ORDER BY CS.FECHASISTEMA DESC
    ) AS Corte
    LEFT JOIN GENERAL.EMPRESA_CIERREHISTORICO AS Cierre
        ON CAST(Cierre.FECHASISTEMA AS date) = Corte.FechaCorte
    OPTION (MAXRECURSION 1200);

    IF (SELECT COUNT(*) FROM @Cortes) <> @CantidadMeses
        THROW 50004, 'No existe una fecha operativa para uno o más meses del rango solicitado.', 1;

    IF EXISTS (
        SELECT 1
        FROM @Cortes
        WHERE FechaCorte < @FechaSistema
          AND (FechaCierreVista IS NULL OR FechaCierreColocacion IS NULL)
    )
        THROW 50005, 'Falta el cierre histórico de vista o colocación para uno o más cortes solicitados.', 1;

    CREATE TABLE #PrestamosPorCliente (
        IdCliente int NOT NULL PRIMARY KEY,
        CantidadPrestamos int NOT NULL,
        TipoPrestamoLista nvarchar(max) NOT NULL,
        ProductoLista nvarchar(max) NOT NULL
    );

    CREATE TABLE #PrestamosDetalle (
        IdCliente int NOT NULL,
        IdPrestamo int NOT NULL,
        TipoPrestamo nvarchar(150) NOT NULL,
        Producto nvarchar(150) NOT NULL,
        PRIMARY KEY (IdCliente, IdPrestamo)
    );

    CREATE TABLE #SaldosPorCuenta (
        NumeroCuenta nvarchar(50) NOT NULL PRIMARY KEY,
        Saldo decimal(18, 6) NOT NULL
    );

    CREATE TABLE #CuentasCorte (
        NumeroCuenta nvarchar(50) NOT NULL PRIMARY KEY,
        IdCliente int NOT NULL,
        FechaUltimaTransaccion datetime NULL
    );

    CREATE TABLE #ClientesCorte (
        IdCliente int NOT NULL PRIMARY KEY
    );

    CREATE TABLE #TasasPorCuenta (
        NumeroCuenta nvarchar(50) NOT NULL PRIMARY KEY,
        Tasa decimal(18, 2) NOT NULL
    );

    CREATE TABLE #TransaccionesPorCuenta (
        NumeroCuenta nvarchar(50) NOT NULL PRIMARY KEY,
        NumeroTransaccionesMes int NOT NULL,
        NumeroDebitosMes int NOT NULL,
        NumeroCreditosMes int NOT NULL
    );

    CREATE TABLE #HechosAhorroVista (
        FechaCorte date NOT NULL,
        NumeroCuenta nvarchar(50) NOT NULL,
        Agencia nvarchar(150) NOT NULL,
        Asesor nvarchar(150) NOT NULL,
        Periodicidad int NULL,
        NumeroTransaccionesMes int NOT NULL,
        NumeroDebitosMes int NOT NULL,
        NumeroCreditosMes int NOT NULL,
        TasaEntera int NOT NULL,
        TasaDecimal decimal(18, 2) NOT NULL,
        Estado nvarchar(150) NOT NULL,
        Provincia nvarchar(150) NOT NULL,
        Canton nvarchar(150) NOT NULL,
        Parroquia nvarchar(150) NOT NULL,
        TienePrestamo bit NOT NULL,
        CantidadPrestamos int NOT NULL,
        TipoPrestamoLista nvarchar(max) NOT NULL,
        ProductoLista nvarchar(max) NOT NULL,
        ProductoAhorro nvarchar(150) NOT NULL,
        EsProgramado bit NOT NULL,
        Saldo decimal(18, 2) NOT NULL,
        PRIMARY KEY (FechaCorte, NumeroCuenta)
    );

    DECLARE
        @FechaCorte date,
        @FechaCierreVista datetime,
        @FechaCierreColocacion datetime;

    DECLARE CursorCortes CURSOR LOCAL FAST_FORWARD FOR
        SELECT FechaCorte, FechaCierreVista, FechaCierreColocacion
        FROM @Cortes
        ORDER BY FechaCorte;

    OPEN CursorCortes;
    FETCH NEXT FROM CursorCortes
        INTO @FechaCorte, @FechaCierreVista, @FechaCierreColocacion;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        TRUNCATE TABLE #PrestamosPorCliente;
        TRUNCATE TABLE #PrestamosDetalle;
        TRUNCATE TABLE #SaldosPorCuenta;
        TRUNCATE TABLE #CuentasCorte;
        TRUNCATE TABLE #ClientesCorte;
        TRUNCATE TABLE #TasasPorCuenta;
        TRUNCATE TABLE #TransaccionesPorCuenta;

        IF @FechaCorte = @FechaSistema
        BEGIN
            INSERT INTO #CuentasCorte (NumeroCuenta, IdCliente, FechaUltimaTransaccion)
            SELECT CU.NUMERO, MIN(CC.IDCLIENTE), MAX(CU.FECHAULTIMATRANSACCION)
            FROM AHORROS.CUENTA AS CU
            INNER JOIN AHORROS.CUENTA_CLIENTE AS CC
                ON CC.NUMEROCUENTA = CU.NUMERO
               AND CC.PRINCIPAL = 1
            INNER JOIN AHORROS.TIPO_CUENTA AS TC
                ON TC.CODIGO = CU.CODIGOTIPOCUENTA
            WHERE CU.CODIGOESTADO IN (N'A', N'I', N'B')
              AND CU.CODIGOTIPOCUENTA <> N'001'
              AND (@EsProgramado IS NULL OR TC.ESPROGRAMADO = @EsProgramado)
            GROUP BY CU.NUMERO;

            INSERT INTO #ClientesCorte (IdCliente)
            SELECT IdCliente
            FROM #CuentasCorte
            GROUP BY IdCliente;

            INSERT INTO #PrestamosDetalle (IdCliente, IdPrestamo, TipoPrestamo, Producto)
            SELECT
                PC.IDCLIENTE,
                P.ID,
                COALESCE(NULLIF(LTRIM(RTRIM(TP.NOMBRE)), N''), N'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(CC.NOMBRE)), N''), N'SIN DATOS')
            FROM COLOCACION.PRESTAMO AS P
            INNER JOIN COLOCACION.PRESTAMO_CLIENTE AS PC
                ON PC.IDPRESTAMO = P.ID
               AND PC.ACTIVO = 1
            INNER JOIN #ClientesCorte AS Clientes
                ON Clientes.IdCliente = PC.IDCLIENTE
            LEFT JOIN CREDITO.TIPO_PRESTAMO AS TP
                ON TP.CODIGO = P.CODIGOTIPOPRESTAMO
            LEFT JOIN CREDITO.CALIFICACION_CONTABLE_SEGMENTO AS CCS
                ON CCS.ID = P.IDCALIFICACIONCONTABLESEGMENTO
            LEFT JOIN CREDITO.CALIFICACION_CONTABLE AS CC
                ON CC.CODIGO = CCS.CODIGOCALIFICACIONCONTABLE
            WHERE P.CODIGOESTADO <> N'C'
            GROUP BY PC.IDCLIENTE, P.ID, TP.NOMBRE, CC.NOMBRE;

            INSERT INTO #PrestamosPorCliente (
                IdCliente, CantidadPrestamos, TipoPrestamoLista, ProductoLista
            )
            SELECT
                D.IdCliente,
                COUNT(D.IdPrestamo),
                COALESCE(STUFF((
                    SELECT NCHAR(8203) + Tipos.TipoPrestamo
                    FROM (
                        SELECT DISTINCT D2.TipoPrestamo
                        FROM #PrestamosDetalle AS D2
                        WHERE D2.IdCliente = D.IdCliente
                    ) AS Tipos
                    ORDER BY Tipos.TipoPrestamo
                    FOR XML PATH(''), TYPE
                ).value('.', 'nvarchar(max)'), 1, 1, N''), N''),
                COALESCE(STUFF((
                    SELECT NCHAR(8203) + Productos.Producto
                    FROM (
                        SELECT DISTINCT D2.Producto
                        FROM #PrestamosDetalle AS D2
                        WHERE D2.IdCliente = D.IdCliente
                    ) AS Productos
                    ORDER BY Productos.Producto
                    FOR XML PATH(''), TYPE
                ).value('.', 'nvarchar(max)'), 1, 1, N''), N'')
            FROM #PrestamosDetalle AS D
            GROUP BY D.IdCliente;

            INSERT INTO #SaldosPorCuenta (NumeroCuenta, Saldo)
            SELECT CI.NUMEROCUENTA, SUM(CI.SALDO)
            FROM #CuentasCorte AS Cuentas
            INNER JOIN AHORROS.CUENTA_ITEMSALDO AS CI
                ON CI.NUMEROCUENTA = Cuentas.NumeroCuenta
            INNER JOIN AHORROS.ITEMSALDO AS ISa
                ON ISa.ID = CI.IDITEM
               AND ISa.SUMASALDO = 1
            GROUP BY CI.NUMEROCUENTA;

            INSERT INTO #TasasPorCuenta (NumeroCuenta, Tasa)
            SELECT S.NumeroCuenta, MAX(IST.TASA)
            FROM #SaldosPorCuenta AS S
            INNER JOIN AHORROS.CUENTA_ITEMSALDO AS CI
                ON CI.NUMEROCUENTA = S.NumeroCuenta
            INNER JOIN AHORROS.ITEMSALDO AS ISa
                ON ISa.ID = CI.IDITEM
               AND ISa.SUMASALDO = 1
            INNER JOIN AHORROS.ITEMSALDO_TASA AS IST
                ON IST.IDITEM = CI.IDITEM
               AND IST.ACTIVO = 1
            WHERE S.Saldo >= IST.SALDOINICIAL
              AND S.Saldo <= IST.SALDOFINAL
            GROUP BY S.NumeroCuenta;

            ;WITH MovimientosUnicos AS (
                SELECT
                    CM.NUMEROCUENTA AS NumeroCuenta,
                    MT.ID AS IdMovimiento,
                    MAX(CASE WHEN MD.DEBITO = 1 THEN 1 ELSE 0 END) AS TieneDebito,
                    MAX(CASE WHEN MD.DEBITO = 0 THEN 1 ELSE 0 END) AS TieneCredito
                FROM FINANCIERO.MOVIMIENTO_TRANSACCION AS MT
                INNER JOIN FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE AS MD
                    ON MD.IDMOVIMIENTOTRANSACCION = MT.ID
                INNER JOIN AHORROS.CUENTA_MOVIMIENTOTRANSACCIONDETALLE AS CM
                    ON CM.IDMOVIMIENTOTRANSACCIONDETALLE = MD.ID
                INNER JOIN #CuentasCorte AS Cuentas
                    ON Cuentas.NumeroCuenta = CM.NUMEROCUENTA
                WHERE MT.FECHASISTEMA >= DATEFROMPARTS(YEAR(@FechaCorte), MONTH(@FechaCorte), 1)
                  AND MT.FECHASISTEMA < DATEADD(day, 1, @FechaCorte)
                  AND MT.ESREVERSO = 0
                GROUP BY CM.NUMEROCUENTA, MT.ID
            )
            INSERT INTO #TransaccionesPorCuenta (
                NumeroCuenta, NumeroTransaccionesMes, NumeroDebitosMes, NumeroCreditosMes
            )
            SELECT
                NumeroCuenta,
                COUNT(*),
                SUM(TieneDebito),
                SUM(TieneCredito)
            FROM MovimientosUnicos
            GROUP BY NumeroCuenta
            OPTION (RECOMPILE);

            INSERT INTO #HechosAhorroVista (
                FechaCorte, NumeroCuenta, Agencia, Asesor, Periodicidad,
                NumeroTransaccionesMes, NumeroDebitosMes, NumeroCreditosMes, TasaEntera, TasaDecimal,
                Estado, Provincia, Canton, Parroquia, TienePrestamo,
                CantidadPrestamos, TipoPrestamoLista, ProductoLista,
                ProductoAhorro, EsProgramado, Saldo
            )
            SELECT
                @FechaCorte,
                CU.NUMERO,
                COALESCE(NULLIF(LTRIM(RTRIM(AG.NOMBRE)), N''), N'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), N''), CU.CODIGOUSUARIOOFICIAL, N'SIN DATOS'),
                Inactividad.Dias,
                COALESCE(Transacciones.NumeroTransaccionesMes, 0),
                COALESCE(Transacciones.NumeroDebitosMes, 0),
                COALESCE(Transacciones.NumeroCreditosMes, 0),
                CONVERT(int, FLOOR(COALESCE(Tasa.Tasa, 0))),
                CONVERT(decimal(18, 2), COALESCE(Tasa.Tasa, 0)),
                COALESCE(NULLIF(LTRIM(RTRIM(EC.NOMBRE)), N''), N'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(DPC.PROVINCIA)), N''), N'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(DPC.CANTON)), N''), N'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(DPC.PARROQUIA)), N''), N'SIN DATOS'),
                CONVERT(bit, CASE WHEN Prestamo.IdCliente IS NULL THEN 0 ELSE 1 END),
                COALESCE(Prestamo.CantidadPrestamos, 0),
                COALESCE(Prestamo.TipoPrestamoLista, N''),
                COALESCE(Prestamo.ProductoLista, N''),
                COALESCE(NULLIF(LTRIM(RTRIM(TipoCuenta.NOMBRE)), N''), N'SIN DATOS'),
                CONVERT(bit, COALESCE(TipoCuenta.ESPROGRAMADO, 0)),
                CONVERT(decimal(18, 2), Saldo.Saldo)
            FROM #CuentasCorte AS Cuentas
            INNER JOIN AHORROS.CUENTA AS CU
                ON CU.NUMERO = Cuentas.NumeroCuenta
            INNER JOIN #SaldosPorCuenta AS Saldo
                ON Saldo.NumeroCuenta = CU.NUMERO
            INNER JOIN CLIENTES.CLIENTE AS C
                ON C.ID = Cuentas.IdCliente
            INNER JOIN SUJETO.PERSONA AS P
                ON P.ID = C.IDPERSONA
            LEFT JOIN GENERAL.AGENCIA AS AG
                ON AG.ID = CU.IDAGENCIA
            LEFT JOIN SEGURIDAD.USUARIO AS U
                ON U.USUARIO = CU.CODIGOUSUARIOOFICIAL
            LEFT JOIN AHORROS.ESTADO_CUENTA AS EC
                ON EC.CODIGO = CU.CODIGOESTADO
            LEFT JOIN GENERAL.DIVISIONPOLITICA_CONSOLIDADO AS DPC
                ON DPC.IDDIVISIONNIVELBAJO = P.IDRESIDENCIA
            LEFT JOIN AHORROS.TIPO_CUENTA AS TipoCuenta
                ON TipoCuenta.CODIGO = CU.CODIGOTIPOCUENTA
            LEFT JOIN #PrestamosPorCliente AS Prestamo
                ON Prestamo.IdCliente = C.ID
            LEFT JOIN #TasasPorCuenta AS Tasa
                ON Tasa.NumeroCuenta = CU.NUMERO
            LEFT JOIN #TransaccionesPorCuenta AS Transacciones
                ON Transacciones.NumeroCuenta = CU.NUMERO
            CROSS APPLY (
                SELECT CASE
                    WHEN CU.FECHAULTIMATRANSACCION IS NULL
                      OR CAST(CU.FECHAULTIMATRANSACCION AS date) > @FechaCorte THEN NULL
                    ELSE DATEDIFF(day, CU.FECHAULTIMATRANSACCION, @FechaCorte)
                END AS Dias
            ) AS Inactividad
            WHERE CU.CODIGOESTADO IN (N'A', N'I', N'B')
              AND CU.CODIGOTIPOCUENTA <> N'001';
        END
        ELSE
        BEGIN
            INSERT INTO #CuentasCorte (NumeroCuenta, IdCliente, FechaUltimaTransaccion)
            SELECT CU.NUMERO, MIN(CC.IDCLIENTE), MAX(CU.FECHAULTIMATRANSACCION)
            FROM AHORROS.CUENTA FOR SYSTEM_TIME AS OF @FechaCierreVista AS CU
            INNER JOIN AHORROS.CUENTA_CLIENTE AS CC
                ON CC.NUMEROCUENTA = CU.NUMERO
               AND CC.PRINCIPAL = 1
            INNER JOIN AHORROS.TIPO_CUENTA AS TC
                ON TC.CODIGO = CU.CODIGOTIPOCUENTA
            WHERE CU.CODIGOESTADO IN (N'A', N'I', N'B')
              AND CU.CODIGOTIPOCUENTA <> N'001'
              AND (@EsProgramado IS NULL OR TC.ESPROGRAMADO = @EsProgramado)
            GROUP BY CU.NUMERO;

            INSERT INTO #ClientesCorte (IdCliente)
            SELECT IdCliente
            FROM #CuentasCorte
            GROUP BY IdCliente;

            INSERT INTO #PrestamosDetalle (IdCliente, IdPrestamo, TipoPrestamo, Producto)
            SELECT
                PC.IDCLIENTE,
                P.ID,
                COALESCE(NULLIF(LTRIM(RTRIM(TP.NOMBRE)), N''), N'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(CC.NOMBRE)), N''), N'SIN DATOS')
            FROM COLOCACION.PRESTAMO FOR SYSTEM_TIME AS OF @FechaCierreColocacion AS P
            INNER JOIN COLOCACION.PRESTAMO_CLIENTE AS PC
                ON PC.IDPRESTAMO = P.ID
               AND PC.ACTIVO = 1
            INNER JOIN #ClientesCorte AS Clientes
                ON Clientes.IdCliente = PC.IDCLIENTE
            LEFT JOIN CREDITO.TIPO_PRESTAMO AS TP
                ON TP.CODIGO = P.CODIGOTIPOPRESTAMO
            LEFT JOIN CREDITO.CALIFICACION_CONTABLE_SEGMENTO AS CCS
                ON CCS.ID = P.IDCALIFICACIONCONTABLESEGMENTO
            LEFT JOIN CREDITO.CALIFICACION_CONTABLE AS CC
                ON CC.CODIGO = CCS.CODIGOCALIFICACIONCONTABLE
            WHERE P.CODIGOESTADO <> N'C'
            GROUP BY PC.IDCLIENTE, P.ID, TP.NOMBRE, CC.NOMBRE;

            INSERT INTO #PrestamosPorCliente (
                IdCliente, CantidadPrestamos, TipoPrestamoLista, ProductoLista
            )
            SELECT
                D.IdCliente,
                COUNT(D.IdPrestamo),
                COALESCE(STUFF((
                    SELECT NCHAR(8203) + Tipos.TipoPrestamo
                    FROM (
                        SELECT DISTINCT D2.TipoPrestamo
                        FROM #PrestamosDetalle AS D2
                        WHERE D2.IdCliente = D.IdCliente
                    ) AS Tipos
                    ORDER BY Tipos.TipoPrestamo
                    FOR XML PATH(''), TYPE
                ).value('.', 'nvarchar(max)'), 1, 1, N''), N''),
                COALESCE(STUFF((
                    SELECT NCHAR(8203) + Productos.Producto
                    FROM (
                        SELECT DISTINCT D2.Producto
                        FROM #PrestamosDetalle AS D2
                        WHERE D2.IdCliente = D.IdCliente
                    ) AS Productos
                    ORDER BY Productos.Producto
                    FOR XML PATH(''), TYPE
                ).value('.', 'nvarchar(max)'), 1, 1, N''), N'')
            FROM #PrestamosDetalle AS D
            GROUP BY D.IdCliente;

            INSERT INTO #SaldosPorCuenta (NumeroCuenta, Saldo)
            SELECT CI.NUMEROCUENTA, SUM(CI.SALDO)
            FROM #CuentasCorte AS Cuentas
            INNER JOIN AHORROS.CUENTA_ITEMSALDO FOR SYSTEM_TIME AS OF @FechaCierreVista AS CI
                ON CI.NUMEROCUENTA = Cuentas.NumeroCuenta
            INNER JOIN AHORROS.ITEMSALDO AS ISa
                ON ISa.ID = CI.IDITEM
               AND ISa.SUMASALDO = 1
            GROUP BY CI.NUMEROCUENTA;

            INSERT INTO #TasasPorCuenta (NumeroCuenta, Tasa)
            SELECT S.NumeroCuenta, MAX(IST.TASA)
            FROM #SaldosPorCuenta AS S
            INNER JOIN AHORROS.CUENTA_ITEMSALDO FOR SYSTEM_TIME AS OF @FechaCierreVista AS CI
                ON CI.NUMEROCUENTA = S.NumeroCuenta
            INNER JOIN AHORROS.ITEMSALDO AS ISa
                ON ISa.ID = CI.IDITEM
               AND ISa.SUMASALDO = 1
            INNER JOIN AHORROS.ITEMSALDO_TASA FOR SYSTEM_TIME AS OF @FechaCierreVista AS IST
                ON IST.IDITEM = CI.IDITEM
               AND IST.ACTIVO = 1
            WHERE S.Saldo >= IST.SALDOINICIAL
              AND S.Saldo <= IST.SALDOFINAL
            GROUP BY S.NumeroCuenta;

            ;WITH MovimientosUnicos AS (
                SELECT
                    CM.NUMEROCUENTA AS NumeroCuenta,
                    MT.ID AS IdMovimiento,
                    MAX(CASE WHEN MD.DEBITO = 1 THEN 1 ELSE 0 END) AS TieneDebito,
                    MAX(CASE WHEN MD.DEBITO = 0 THEN 1 ELSE 0 END) AS TieneCredito
                FROM FINANCIERO.MOVIMIENTO_TRANSACCION AS MT
                INNER JOIN FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE AS MD
                    ON MD.IDMOVIMIENTOTRANSACCION = MT.ID
                INNER JOIN AHORROS.CUENTA_MOVIMIENTOTRANSACCIONDETALLE AS CM
                    ON CM.IDMOVIMIENTOTRANSACCIONDETALLE = MD.ID
                INNER JOIN #CuentasCorte AS Cuentas
                    ON Cuentas.NumeroCuenta = CM.NUMEROCUENTA
                WHERE MT.FECHASISTEMA >= DATEFROMPARTS(YEAR(@FechaCorte), MONTH(@FechaCorte), 1)
                  AND MT.FECHASISTEMA < DATEADD(day, 1, @FechaCorte)
                  AND MT.ESREVERSO = 0
                GROUP BY CM.NUMEROCUENTA, MT.ID
            )
            INSERT INTO #TransaccionesPorCuenta (
                NumeroCuenta, NumeroTransaccionesMes, NumeroDebitosMes, NumeroCreditosMes
            )
            SELECT
                NumeroCuenta,
                COUNT(*),
                SUM(TieneDebito),
                SUM(TieneCredito)
            FROM MovimientosUnicos
            GROUP BY NumeroCuenta
            OPTION (RECOMPILE);

            INSERT INTO #HechosAhorroVista (
                FechaCorte, NumeroCuenta, Agencia, Asesor, Periodicidad,
                NumeroTransaccionesMes, NumeroDebitosMes, NumeroCreditosMes, TasaEntera, TasaDecimal,
                Estado, Provincia, Canton, Parroquia, TienePrestamo,
                CantidadPrestamos, TipoPrestamoLista, ProductoLista,
                ProductoAhorro, EsProgramado, Saldo
            )
            SELECT
                @FechaCorte,
                CU.NUMERO,
                COALESCE(NULLIF(LTRIM(RTRIM(AG.NOMBRE)), N''), N'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(U.NOMBRE)), N''), CU.CODIGOUSUARIOOFICIAL, N'SIN DATOS'),
                Inactividad.Dias,
                COALESCE(Transacciones.NumeroTransaccionesMes, 0),
                COALESCE(Transacciones.NumeroDebitosMes, 0),
                COALESCE(Transacciones.NumeroCreditosMes, 0),
                CONVERT(int, FLOOR(COALESCE(Tasa.Tasa, 0))),
                CONVERT(decimal(18, 2), COALESCE(Tasa.Tasa, 0)),
                COALESCE(NULLIF(LTRIM(RTRIM(EC.NOMBRE)), N''), N'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(DPC.PROVINCIA)), N''), N'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(DPC.CANTON)), N''), N'SIN DATOS'),
                COALESCE(NULLIF(LTRIM(RTRIM(DPC.PARROQUIA)), N''), N'SIN DATOS'),
                CONVERT(bit, CASE WHEN Prestamo.IdCliente IS NULL THEN 0 ELSE 1 END),
                COALESCE(Prestamo.CantidadPrestamos, 0),
                COALESCE(Prestamo.TipoPrestamoLista, N''),
                COALESCE(Prestamo.ProductoLista, N''),
                COALESCE(NULLIF(LTRIM(RTRIM(TipoCuenta.NOMBRE)), N''), N'SIN DATOS'),
                CONVERT(bit, COALESCE(TipoCuenta.ESPROGRAMADO, 0)),
                CONVERT(decimal(18, 2), Saldo.Saldo)
            FROM #CuentasCorte AS Cuentas
            INNER JOIN AHORROS.CUENTA FOR SYSTEM_TIME AS OF @FechaCierreVista AS CU
                ON CU.NUMERO = Cuentas.NumeroCuenta
            INNER JOIN #SaldosPorCuenta AS Saldo
                ON Saldo.NumeroCuenta = CU.NUMERO
            INNER JOIN CLIENTES.CLIENTE AS C
                ON C.ID = Cuentas.IdCliente
            INNER JOIN SUJETO.PERSONA AS P
                ON P.ID = C.IDPERSONA
            LEFT JOIN GENERAL.AGENCIA AS AG
                ON AG.ID = CU.IDAGENCIA
            LEFT JOIN SEGURIDAD.USUARIO AS U
                ON U.USUARIO = CU.CODIGOUSUARIOOFICIAL
            LEFT JOIN AHORROS.ESTADO_CUENTA AS EC
                ON EC.CODIGO = CU.CODIGOESTADO
            LEFT JOIN GENERAL.DIVISIONPOLITICA_CONSOLIDADO AS DPC
                ON DPC.IDDIVISIONNIVELBAJO = P.IDRESIDENCIA
            LEFT JOIN AHORROS.TIPO_CUENTA AS TipoCuenta
                ON TipoCuenta.CODIGO = CU.CODIGOTIPOCUENTA
            LEFT JOIN #PrestamosPorCliente AS Prestamo
                ON Prestamo.IdCliente = C.ID
            LEFT JOIN #TasasPorCuenta AS Tasa
                ON Tasa.NumeroCuenta = CU.NUMERO
            LEFT JOIN #TransaccionesPorCuenta AS Transacciones
                ON Transacciones.NumeroCuenta = CU.NUMERO
            CROSS APPLY (
                SELECT CASE
                    WHEN CU.FECHAULTIMATRANSACCION IS NULL
                      OR CAST(CU.FECHAULTIMATRANSACCION AS date) > @FechaCorte THEN NULL
                    ELSE DATEDIFF(day, CU.FECHAULTIMATRANSACCION, @FechaCorte)
                END AS Dias
            ) AS Inactividad
            WHERE CU.CODIGOESTADO IN (N'A', N'I', N'B')
              AND CU.CODIGOTIPOCUENTA <> N'001';
        END;

        FETCH NEXT FROM CursorCortes
            INTO @FechaCorte, @FechaCierreVista, @FechaCierreColocacion;
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
        H.Periodicidad AS periodicidad,
        SUM(H.NumeroTransaccionesMes) AS numero_transacciones_mes,
        SUM(H.NumeroDebitosMes) AS numero_debitos_mes,
        SUM(H.NumeroCreditosMes) AS numero_creditos_mes,
        H.TasaEntera AS tasa_entera,
        H.TasaDecimal AS tasa_decimal,
        H.Periodicidad AS tiempo_inactivo_dias,
        H.Estado AS estado,
        H.Provincia AS provincia,
        H.Canton AS canton,
        H.Parroquia AS parroquia,
        H.TienePrestamo AS tiene_prestamo,
        H.CantidadPrestamos AS cantidad_prestamos,
        H.TipoPrestamoLista AS tipo_prestamo_lista,
        H.ProductoLista AS producto_lista,
        H.ProductoAhorro AS producto_ahorro,
        H.EsProgramado AS es_programado,
        SUM(H.Saldo) AS saldo
    FROM #HechosAhorroVista AS H
    GROUP BY
        H.FechaCorte, H.Agencia, H.Asesor, H.Periodicidad,
        H.TasaEntera, H.TasaDecimal, H.Estado,
        H.Provincia, H.Canton, H.Parroquia, H.TienePrestamo,
        H.CantidadPrestamos, H.TipoPrestamoLista, H.ProductoLista,
        H.ProductoAhorro, H.EsProgramado
    ORDER BY
        H.FechaCorte, H.Agencia, H.Asesor, H.Periodicidad,
        H.Estado
    OPTION (RECOMPILE);
END;
GO

/*
EXEC AHORROS.REPORTE_ANALITICO_AHORROS_VISTA
    @FechaInicio = '2026-07-01',
    @FechaFin = '2026-07-31',
    @EsProgramado = NULL;
*/

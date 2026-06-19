from app.modules.prestamos.repositories.sql_universo_repository import SqlUniversoPrestamosRepository


class FakeResult:
    def mappings(self) -> "FakeResult":
        return self

    def all(self) -> list:
        return []


class FakeSession:
    def __init__(self) -> None:
        self.last_statement = None

    def execute(self, statement):
        self.last_statement = str(statement)
        return FakeResult()


def test_get_prestamos_actuales_crea_prestamos_base_sin_order_by_si_no_hay_limit() -> None:
    session = FakeSession()
    repository = SqlUniversoPrestamosRepository(session)

    repository.get_prestamos_actuales()

    prestamos_base_sql = session.last_statement.split("INTO #PrestamosBase", 1)[0]
    assert "SELECT \n" in prestamos_base_sql
    assert "INTO #PrestamosBase" in session.last_statement
    assert "ORDER BY P.ID" not in prestamos_base_sql
    assert "ORDER BY PB.IdPrestamo" in session.last_statement


def test_get_prestamos_actuales_agrega_top_y_order_by_en_base_con_limit() -> None:
    session = FakeSession()
    repository = SqlUniversoPrestamosRepository(session)

    repository.get_prestamos_actuales(limit=100)

    prestamos_base_sql = session.last_statement.split("INTO #PrestamosBase", 1)[0]
    assert "SELECT TOP (100)" in prestamos_base_sql
    assert "ORDER BY P.ID" in session.last_statement
    assert "P.CODIGOUSUARIO AS CodigoAsesor" in session.last_statement
    assert "P.CODIGOUSUARIO AS CodigoUsuario" not in session.last_statement
    assert "\n                PB.CodigoUsuario,\n" not in session.last_statement


def test_get_prestamos_actuales_calcula_capital_y_exigibles_desde_rubros_pendientes() -> None:
    session = FakeSession()
    repository = SqlUniversoPrestamosRepository(session)

    repository.get_prestamos_actuales(limit=100)

    assert "INTO #RubrosPendientes" in session.last_statement
    assert "CREATE NONCLUSTERED INDEX IX_RubrosPendientes_IdPrestamo" in session.last_statement
    assert "FROM #RubrosPendientes" in session.last_statement
    assert "EsNoDevenga" in session.last_statement
    assert "EsVencido" in session.last_statement
    assert "ExigiblesClasificados AS" in session.last_statement
    assert "INNER JOIN #PrestamosBase PB" in session.last_statement
    assert "PC.VALORALDIA" in session.last_statement
    assert "PC.VALORALDIAMASCUOTACTUAL" in session.last_statement
    assert "PC.VALORCANCELAPRESTAMO" in session.last_statement


def test_get_prestamos_actuales_trae_parametros_de_provision_con_outer_apply() -> None:
    session = FakeSession()
    repository = SqlUniversoPrestamosRepository(session)

    repository.get_prestamos_actuales(limit=100)

    assert "OUTER APPLY" in session.last_statement
    assert "SELECT TOP 1" in session.last_statement
    assert "COLOCACION.PRESTAMO_CALIFICACION PCAL" in session.last_statement
    assert "WHERE PCAL.IDPRESTAMO = PB.IdPrestamo" in session.last_statement
    assert "ORDER BY PCAL.FECHACALIFICACION DESC, PCAL.ID DESC" in session.last_statement
    assert "CALIFICACION_PRESTAMO_INFORMACION CPI" in session.last_statement
    assert "PCAL.SALDO AS SaldoBaseProvision" in session.last_statement
    assert "PCAL.PORCENTAJE_FIJO AS PorcentajeProvisionFuente" in session.last_statement
    assert "CPI.PORCENTAJE_MINIMO, 0) AS PorcentajeProvisionMinimo" in session.last_statement
    assert "CPI.PORCENTAJE_MAXIMO, 0) AS PorcentajeProvisionMaximo" in session.last_statement
    assert "CPI.ESPORCENTAJE_FIJO, 0) AS EsPorcentajeFijo" in session.last_statement
    assert "ROW_NUMBER()" not in session.last_statement


def test_get_prestamos_actuales_trae_responsables_cargo_y_provincia() -> None:
    session = FakeSession()
    repository = SqlUniversoPrestamosRepository(session)

    repository.get_prestamos_actuales(limit=100)

    assert "E.IDCARGO AS IdCargoAsesor" in session.last_statement
    assert "CAR.NOMBRE AS CargoAsesor" in session.last_statement
    assert "COLOCACION.PRESTAMO_USUARIO_CONTROL PUC" in session.last_statement
    assert "PUC.CODIGOUSUARIOCONTROL AS CodigoUsuarioControl" in session.last_statement
    assert "PUC.CODIGOUSUARIOCOBRANZAAPOYO AS CodigoUsuarioCobranzaApoyo" in session.last_statement
    assert "NULLIF(LTRIM(RTRIM(PUC.CODIGOUSUARIOCONTROL)), '') IS NOT NULL" in session.last_statement
    assert "NULLIF(LTRIM(RTRIM(PUC.CODIGOUSUARIOCOBRANZAAPOYO)), '') IS NOT NULL" in session.last_statement
    assert "APOYO.CodigoUsuarioCobranzaApoyo AS CodigoUsuarioCobranzaApoyo" in session.last_statement
    assert "UCTRL.NOMBRE AS UsuarioControl" in session.last_statement
    assert "UAPOYO.NOMBRE AS CobranzaApoyo" in session.last_statement
    assert "GENERAL.DIVISIONPOLITICA_CONSOLIDADO DPC" in session.last_statement
    assert "DPC.PROVINCIA AS Provincia" in session.last_statement

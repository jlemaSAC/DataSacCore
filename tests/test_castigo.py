from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.recuperacion.castigo.dependencies import get_castigo_service
from app.modules.negocios.recuperacion.castigo.repositories.mongo_castigo_repository import MongoCastigoRepository
from app.modules.negocios.recuperacion.castigo.repositories.sql_castigo_repository import SqlCastigoRepository
from app.modules.negocios.recuperacion.castigo.schemas import InputDepositosCastigo, InputDetalleDepositosCastigo
from app.modules.negocios.recuperacion.castigo.service import CastigoService


class Cursor(list):
    def max_time_ms(self, _):
        return self


def coincide(documento, query):
    for campo, valor in query.items():
        if campo == '$or':
            if not any(coincide(documento, opcion) for opcion in valor):
                return False
        elif isinstance(valor, dict):
            dato = documento.get(campo)
            for operador, limite in valor.items():
                if operador == '$in' and dato not in limite:
                    return False
                if operador == '$gte' and (dato is None or dato < limite):
                    return False
                if operador == '$lte' and (dato is None or dato > limite):
                    return False
        elif documento.get(campo) != valor:
            return False
    return True


class Collection:
    def __init__(self, documentos):
        self.documentos = documentos
        self.queries = []

    def find(self, query, projection):
        self.queries.append(query)
        return Cursor([{campo: valor for campo, valor in documento.items() if projection.get(campo)} for documento in self.documentos if coincide(documento, query)])

    def distinct(self, campo, query, **_):
        return list({d[campo] for d in self.documentos if coincide(d, query)})

    def find_one(self, query, projection):
        return next(iter(self.find(query, projection)), None)


class SqlFake:
    def __init__(self, montos=None):
        self.montos = montos or {}
        self.llamadas = []
        self.llamadas_movimientos = []

    def obtener_depositos_mes(self, numeros, fecha):
        self.llamadas.append((numeros, fecha))
        return self.montos

    def obtener_movimientos(self, numeros, desde, hasta, pagina, tamano):
        self.llamadas_movimientos.append((numeros, desde, hasta, pagina, tamano))
        return [], 0, Decimal(0)


def documento(numero, dia, monto, estado='CASTIGADO', **extra):
    return {'NumeroPrestamo': numero, 'fecha_corte': f'202610{dia:02}', 'DepositosMes': monto,
            'EstadoPrestamo': estado, 'Cliente': 100, 'Agencia': 'MATRIZ',
            'CodigoAsesor': '01', 'NombreAsesor': 'ANA', 'CargoAsesor': 'GESTOR', **extra}


def contexto():
    return AuthContext.from_token_payload('token', UsuarioTokenPayload(sub='test', usuario='Test', id_agencia=1, nombre_agencia='MATRIZ', fecha_sistema=date(2026, 10, 20)))


def servicio(documentos, actuales=None, sql=None):
    db = {'SituacionCrediticia': Collection(documentos), 'SituacionCrediticiaActual': Collection(actuales or [])}
    return CastigoService(MongoCastigoRepository(db), sql or SqlFake()), db


def consultar(service, inicio=1, fin=3, **filtros):
    return service.obtener_depositos_diarios(InputDepositosCastigo(fecha_desde=date(2026, 10, inicio), fecha_hasta=date(2026, 10, fin), **filtros), contexto())


def test_fija_universo_inicial_sin_filtrar_ceros_y_conserva_cancelados_y_dimensiones():
    service, db = servicio([
        documento('P1', 1, 0), documento('P1', 2, 100, 'CANCELADO', Agencia='OTRA', NombreAsesor='OTRO', CargoAsesor='OTRO'),
        documento('P1', 3, 150, 'CANCELADO'),
        documento('P2', 1, 10, 'JUDICIAL'), documento('P2', 2, 10, 'JUDICIAL'), documento('P2', 3, 30, 'JUDICIAL'),
        documento('P3', 1, 0, 'AL DIA'), documento('P3', 2, 1000, 'CASTIGADO'), documento('P3', 3, 2000, 'CASTIGADO'),
    ])
    resultado = consultar(service, agencias=['matriz'], cargos=['gestor'])
    assert resultado.total_depositado == 180
    p1 = [d for d in resultado.depositos if d.numero_prestamo == 'P1']
    assert [(d.fecha.day, d.total_depositado) for d in p1] == [(2, 100), (3, 50)]
    assert all((d.agencia, d.asesor, d.cargo_asesor, d.estado_inicio, d.estado_fin) == ('MATRIZ', 'ANA', 'GESTOR', 'CASTIGADO', 'CANCELADO') for d in p1)
    assert all(d.numero_prestamo != 'P3' for d in resultado.depositos)
    assert resultado.catalogos.cargos == ['GESTOR']
    assert 'EstadoPrestamo' not in db['SituacionCrediticia'].queries[-1]


def test_conserva_prestamo_sin_movimientos_y_las_correcciones_negativas():
    service, _ = servicio([documento('P1', 1, 0), documento('P1', 2, 0), documento('P1', 3, 0),
                            documento('P2', 1, 100), documento('P2', 2, 80), documento('P2', 3, 80)])
    resultado = consultar(service)
    assert [(d.numero_prestamo, d.fecha.day, d.total_depositado) for d in resultado.depositos] == [('P2', 1, 100), ('P2', 2, -20), ('P1', 3, 0)]
    assert resultado.total_depositado == 80


def test_rango_parcial_resta_corte_previo_en_lugar_de_contar_acumulado_completo():
    service, _ = servicio([documento('P1', 1, 100), documento('P1', 2, 125.25), documento('P1', 3, 200.5)])
    resultado = consultar(service, inicio=2)
    assert [(d.fecha.day, d.total_depositado) for d in resultado.depositos] == [(2, 25.25), (3, 75.25)]
    assert resultado.total_depositado == 100.5


def test_primer_dia_no_resta_el_acumulado_del_mes_anterior():
    service, _ = servicio([documento('P1', 1, 15), documento('P1', 1, 999, fecha_corte='20260930')])
    assert consultar(service, fin=1).total_depositado == 15


def test_seguimiento_es_por_prestamo_aunque_compartan_cliente():
    service, _ = servicio([documento('P1', 1, 20, Cliente=1), documento('P2', 1, 20, 'JUDICIAL', Cliente=1)])
    resultado = consultar(service, fin=1)
    assert len(resultado.depositos) == 2
    assert resultado.total_depositado == 40


def test_corte_actual_sql_completa_el_acumulado_sin_descartar_estado_cancelado():
    sql = SqlFake({'P1': Decimal(170)})
    service, _ = servicio([documento('P1', 19, 100)], [documento('P1', 20, None, 'CANCELADO', as_of=datetime(2026, 10, 20, 12, tzinfo=timezone.utc))], sql)
    resultado = consultar(service, inicio=20, fin=20)
    # El inicio en el día actual debe excluir a los que YA estaban cancelados.
    assert resultado.depositos == []
    assert sql.llamadas == []
    service, _ = servicio([documento('P1', 18, 50), documento('P1', 19, 100)], [documento('P1', 20, None, 'CANCELADO', as_of=datetime(2026, 10, 20, 12, tzinfo=timezone.utc))], sql)
    resultado = consultar(service, inicio=19, fin=20)
    assert [(d.fecha.day, d.total_depositado, d.estado_fin) for d in resultado.depositos] == [(19, 50, 'CANCELADO'), (20, 70, 'CANCELADO')]
    assert sql.llamadas == [(['P1'], date(2026, 10, 20))]


def test_inicio_en_fecha_actual_usa_dimensiones_actuales_y_base_historica():
    sql = SqlFake({'P1': Decimal(170)})
    service, _ = servicio(
        [documento('P1', 19, 100)],
        [documento('P1', 20, None, as_of=datetime(2026, 10, 20, 12, tzinfo=timezone.utc))],
        sql,
    )
    resultado = consultar(service, inicio=20, fin=20)
    assert [(d.fecha.day, d.total_depositado) for d in resultado.depositos] == [(20, 70)]


def test_un_importe_sql_ausente_no_se_interpreta_como_cero():
    service, _ = servicio(
        [documento('P1', 19, 100)],
        [documento('P1', 20, None, as_of=datetime(2026, 10, 20, 12, tzinfo=timezone.utc))],
        SqlFake(),
    )
    with pytest.raises(HTTPException) as error:
        consultar(service, inicio=20, fin=20)
    assert error.value.status_code == 409


def test_un_corte_duplicado_no_duplica_depositos_del_prestamo():
    service, _ = servicio([documento('P1', 1, 10), documento('P1', 1, 10)])
    resultado = consultar(service, fin=1)
    assert len(resultado.depositos) == 1
    assert resultado.total_depositado == 10


@pytest.mark.parametrize('documentos', [
    [documento('P1', 1, 10), documento('P1', 3, 20)],
    [documento('P1', 1, 10), documento('P1', 3, 20), documento('P2', 1, 0), documento('P2', 2, 0), documento('P2', 3, 0)],
    [documento('P1', 1, 10), documento('P1', 2, None), documento('P1', 3, 20)],
])
def test_corte_ausente_o_sin_campo_no_se_convierte_en_deposito_cero(documentos):
    service, _ = servicio(documentos)
    with pytest.raises(HTTPException) as error:
        consultar(service)
    assert error.value.status_code == 409


def test_rechaza_rangos_entre_meses_y_fechas_futuras():
    with pytest.raises(ValidationError, match='mismo mes'):
        InputDepositosCastigo(fecha_desde=date(2026, 9, 30), fecha_hasta=date(2026, 10, 2))
    service, _ = servicio([])
    with pytest.raises(HTTPException) as error:
        consultar(service, fin=21)
    assert error.value.status_code == 400


def test_sql_solo_consulta_el_universo_mediante_parametros_y_replica_depositos_mes():
    class Filas(list):
        def mappings(self):
            return self
    class Db:
        def execute(self, statement, params):
            self.statement = statement
            self.params = params
            return Filas([{'NumeroPrestamo': 'P1', 'DepositosMes': 125}])
    db = Db()
    valores = SqlCastigoRepository(db).obtener_depositos_mes(['P1'], date(2026, 10, 20))
    assert valores == {'P1': Decimal(125)}
    assert db.params == {
        'numeros': ['P1'], 'inicio_mes': date(2026, 10, 1),
        'fin_exclusivo': date(2026, 10, 21),
        'transacciones_excluidas': (33, 34, 2092, 2093, 2095, 2105),
    }
    assert 'P1' not in str(db.statement)
    assert 'MD.DEBITO = 0' in str(db.statement)
    assert 'CC.PRINCIPAL = 1' in str(db.statement)
    assert 'CAST(COALESCE(D.TOTAL, 0) AS INT)' in str(db.statement)


def test_endpoint_conserva_alias_diarios_y_autenticacion_bearer():
    service, _ = servicio([documento('P1', 1, 0), documento('P1', 2, 10, 'CANCELADO')])
    client = TestClient(app)
    app.dependency_overrides[get_castigo_service] = lambda: service
    app.dependency_overrides[get_current_auth_context] = contexto
    try:
        response = client.post('/negocios/recuperacion/castigo/depositos-diarios', json={'fecha_desde': '2026-10-01', 'fecha_hasta': '2026-10-02', 'agencias': ['MATRIZ']})
        assert response.status_code == 200
        body = response.json()
        assert body['TotalDepositado'] == 10
        assert body['Depositos'][0]['Fecha'] == '2026-10-02'
        assert body['Depositos'][0]['EstadoPrestamoInicio'] == 'CASTIGADO'
        assert body['Depositos'][0]['EstadoPrestamoFin'] == 'CANCELADO'
        assert body['Depositos'][0]['TipoTransaccion'] == 'VARIACION DEPOSITOS MES'
        del app.dependency_overrides[get_current_auth_context]
        assert client.post('/negocios/recuperacion/castigo/depositos-diarios', json={'fecha_desde': '2026-10-01', 'fecha_hasta': '2026-10-02'}).status_code == 401
    finally:
        app.dependency_overrides.pop(get_castigo_service, None)
        app.dependency_overrides.pop(get_current_auth_context, None)


def test_detalle_verifica_universo_inicial_y_solo_busca_movimientos_de_la_celda():
    sql = SqlFake()
    service, _ = servicio([
        documento('P1', 1, 0), documento('P1', 2, 10, 'CANCELADO'), documento('P1', 3, 20, 'CANCELADO'),
        documento('P2', 1, 20, 'AL DIA'), documento('P2', 2, 200, 'CASTIGADO'), documento('P2', 3, 300, 'CASTIGADO'),
    ], sql=sql)
    request = InputDetalleDepositosCastigo(fecha_desde=date(2026,10,1), fecha_hasta=date(2026,10,3),
        numeros_prestamo=['P1', 'P2'], fecha_deposito=date(2026,10,2), pagina=2, tamano_pagina=10)
    resultado = service.obtener_detalle_depositos(request, contexto())
    assert resultado.total_depositado == 10
    assert [(d.numero_prestamo, d.fecha.day, d.estado_fin) for d in resultado.depositos] == [('P1', 2, 'CANCELADO')]
    assert sql.llamadas_movimientos == [(['P1'], date(2026,10,2), date(2026,10,2), 2, 10)]
    assert resultado.pagina == 2
    request.fecha_deposito = None
    resultado = service.obtener_detalle_depositos(request, contexto())
    assert resultado.total_depositado == 20
    assert sql.llamadas_movimientos[-1][1:3] == (date(2026,10,1), date(2026,10,3))


def test_detalle_respeta_agencia_inicial_y_no_amplia_prestamos_solicitados():
    sql = SqlFake()
    service, _ = servicio([documento('P1', 1, 10), documento('P2', 1, 20, Agencia='NORTE')], sql=sql)
    request = InputDetalleDepositosCastigo(fecha_desde=date(2026,10,1), fecha_hasta=date(2026,10,1),
        agencias=['MATRIZ'], numeros_prestamo=['P2'])
    resultado = service.obtener_detalle_depositos(request, contexto())
    assert resultado.depositos == []
    assert resultado.total_depositado == 0
    assert sql.llamadas_movimientos[0][0] == []


def test_detalle_rechaza_fecha_fuera_del_periodo_o_listas_sin_prestamos():
    with pytest.raises(ValidationError, match='dentro del rango'):
        InputDetalleDepositosCastigo(fecha_desde=date(2026,10,1), fecha_hasta=date(2026,10,3),
            numeros_prestamo=['P1'], fecha_deposito=date(2026,10,4))
    with pytest.raises(ValidationError):
        InputDetalleDepositosCastigo(fecha_desde=date(2026,10,1), fecha_hasta=date(2026,10,3), numeros_prestamo=[' '])


def test_sql_detalle_pagina_y_totales_usan_clientes_unicos_y_xml_parametrizado():
    class Resumen:
        def mappings(self): return self
        def one(self): return {'Cantidad': 51, 'Total': Decimal('125.25')}
    class Movimientos:
        def mappings(self): return self
        def all(self): return []
    class Db:
        def __init__(self): self.llamadas = []
        def execute(self, statement, params):
            self.llamadas.append((str(statement), params))
            return Resumen() if len(self.llamadas) == 1 else Movimientos()
    db = Db()
    filas, cantidad, monto = SqlCastigoRepository(db).obtener_movimientos(["N<&", "N<&"], date(2026,10,2), date(2026,10,2), 2, 50)
    assert (filas, cantidad, monto) == ([], 51, Decimal('125.25'))
    sql, params = db.llamadas[-1]
    assert 'SELECT DISTINCT IDCLIENTE FROM PrestamosElegibles' in sql
    assert 'OFFSET :offset ROWS' in sql
    assert "N<&" not in sql
    assert params['prestamos_xml'] == '<prestamos><prestamo>N&lt;&amp;</prestamo></prestamos>'
    assert params['offset'] == 50
    assert params['fin_exclusivo'] == date(2026,10,3)
    for statement, parametros in db.llamadas:
        assert 'M.IDTRANSACCION NOT IN' in statement
        assert parametros['transacciones_excluidas'] == (33, 34, 2092, 2093, 2095, 2105)


def test_bloqueos_antiguos_no_generan_depositos_ficticios_en_el_corte_actual():
    # Ejecuta el cálculo real del acumulado con datos aislados: dos depósitos y
    # las seis transacciones contables que el reporte histórico excluye.
    engine = create_engine('sqlite://')
    try:
        with engine.connect() as connection:
            for schema in ('COLOCACION', 'FINANCIERO', 'AHORROS'):
                connection.exec_driver_sql(f"ATTACH DATABASE ':memory:' AS {schema}")
            tablas = {
                'COLOCACION.PRESTAMO': 'ID INT, NUMERO TEXT',
                'COLOCACION.PRESTAMO_CLIENTE': 'IDPRESTAMO INT, IDCLIENTE INT, ESPRINCIPAL INT',
                'FINANCIERO.MOVIMIENTO_TRANSACCION': 'ID INT, IDTRANSACCION INT, FECHASISTEMA DATE',
                'FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE': 'ID INT, IDMOVIMIENTOTRANSACCION INT, DEBITO INT, VALOR NUMERIC',
                'AHORROS.CUENTA_MOVIMIENTOTRANSACCIONDETALLE': 'IDMOVIMIENTOTRANSACCIONDETALLE INT, NUMEROCUENTA TEXT',
                'AHORROS.CUENTA': 'NUMERO TEXT',
                'AHORROS.CUENTA_CLIENTE': 'NUMEROCUENTA TEXT, IDCLIENTE INT, PRINCIPAL INT',
            }
            for tabla, columnas in tablas.items():
                connection.exec_driver_sql(f'CREATE TABLE {tabla} ({columnas})')
            connection.exec_driver_sql("INSERT INTO COLOCACION.PRESTAMO VALUES (1, 'P1')")
            connection.exec_driver_sql('INSERT INTO COLOCACION.PRESTAMO_CLIENTE VALUES (1, 1, 1)')
            connection.exec_driver_sql("INSERT INTO AHORROS.CUENTA VALUES ('C1')")
            connection.exec_driver_sql("INSERT INTO AHORROS.CUENTA_CLIENTE VALUES ('C1', 1, 1)")
            movimientos = [(110, '2026-10-07', 283.33), (110, '2026-10-16', 40)] + [
                (tipo, '2026-10-16', 100) for tipo in (33, 34, 2092, 2093, 2095, 2105)
            ]
            for indice, (tipo, fecha, valor) in enumerate(movimientos, 1):
                connection.execute(text('INSERT INTO FINANCIERO.MOVIMIENTO_TRANSACCION VALUES (:id, :tipo, :fecha)'), {'id': indice, 'tipo': tipo, 'fecha': fecha})
                connection.execute(text('INSERT INTO FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE VALUES (:id, :id, 0, :valor)'), {'id': indice, 'valor': valor})
                connection.execute(text("INSERT INTO AHORROS.CUENTA_MOVIMIENTOTRANSACCIONDETALLE VALUES (:id, 'C1')"), {'id': indice})
            with Session(bind=connection) as session:
                repo = SqlCastigoRepository(session)
                assert repo.obtener_depositos_mes(['P1'], date(2026, 10, 20)) == {'P1': Decimal(323)}
                service, _ = servicio(
                    [documento('P1', 19, 323)],
                    [documento('P1', 20, None, as_of=datetime(2026, 10, 20, 12, tzinfo=timezone.utc))],
                    repo,
                )
                resultado = consultar(service, inicio=20, fin=20)
                assert resultado.total_depositado == 0
                assert resultado.depositos[0].total_depositado == 0
    finally:
        engine.dispose()


def test_endpoint_detalle_requiere_bearer_y_conserva_los_cancelados():
    service, _ = servicio([documento('P1', 1, 0), documento('P1', 2, 10, 'CANCELADO')])
    client = TestClient(app)
    app.dependency_overrides[get_castigo_service] = lambda: service
    app.dependency_overrides[get_current_auth_context] = contexto
    body = {'fecha_desde': '2026-10-01', 'fecha_hasta': '2026-10-02', 'numeros_prestamo': ['P1'], 'fecha_deposito': '2026-10-02'}
    try:
        response = client.post('/negocios/recuperacion/castigo/depositos-diarios/detalle', json=body)
        assert response.status_code == 200
        assert response.json()['TotalDepositado'] == 10
        assert response.json()['Depositos'][0]['EstadoPrestamoFin'] == 'CANCELADO'
        assert response.json()['TotalMovimientos'] == 0
        del app.dependency_overrides[get_current_auth_context]
        assert client.post('/negocios/recuperacion/castigo/depositos-diarios/detalle', json=body).status_code == 401
    finally:
        app.dependency_overrides.pop(get_castigo_service, None)
        app.dependency_overrides.pop(get_current_auth_context, None)


def test_detalle_puede_listar_prestamos_sin_consultar_movimientos_en_cuentas():
    sql = SqlFake()
    service, _ = servicio([documento('P1', 1, 0), documento('P1', 2, 10, 'CANCELADO')], sql=sql)
    request = InputDetalleDepositosCastigo(
        fecha_desde=date(2026, 10, 1), fecha_hasta=date(2026, 10, 2),
        numeros_prestamo=['P1'], incluir_movimientos=False,
    )
    resultado = service.obtener_detalle_depositos(request, contexto())
    assert resultado.total_depositado == 10
    assert resultado.depositos[0].numero_prestamo == 'P1'
    assert resultado.movimientos == []
    assert resultado.total_movimientos == 0
    assert resultado.total_creditos_cuenta == 0
    assert sql.llamadas_movimientos == []

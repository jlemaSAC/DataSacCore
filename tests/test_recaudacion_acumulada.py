from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.recuperacion.recaudacion_acumulada.dependencies import (
    get_asesores_agencia_service,
    get_recaudacion_acumulada_service,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.domain import (
    DetalleCuotaPrestamo,
    RecuperacionPrestamo,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.schemas import (
    AsesorAgenciaResponse,
    InputAsesoresPorAgencia,
    InputRecaudacionAcumulada,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.service import (
    RecaudacionAcumuladaService,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.repositories.sql_detalle_cuotas_repository import (
    SqlDetalleCuotasRepository,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.repositories import (
    sql_detalle_cuotas_repository as sql_repository_module,
)


client = TestClient(app)


def auth_context(fecha_sistema: date = date(2026, 9, 14)) -> AuthContext:
    return AuthContext.from_token_payload(
        "token",
        UsuarioTokenPayload(
            sub="jdoe",
            usuario="John Doe",
            id_agencia=1,
            nombre_agencia="Matriz",
            fecha_sistema=fecha_sistema,
        ),
    )


class FakeMongoRepository:
    def __init__(self) -> None:
        self.filtros: tuple[list[str], list[str]] | None = None

    def existe_corte(self, fecha_corte, fecha_actual):
        return True

    def obtener_corte_inicial(self, fecha_corte, numeros_prestamo):
        assert fecha_corte == date(2026, 8, 31)
        assert set(numeros_prestamo) == {"0001", "0002", "0003"}
        return {
            "0001": {
                "NumeroPrestamo": "0001",
                "EstadoPrestamo": "VIGENTE",
                "Calificacion": "B-1",
                "DiasVencidos": 10,
                "SaldoCapital": 1200,
                "ProvisionRequerida": 120,
                "Cliente": 7,
                "Nombres": "SOCIO UNO",
                "Identificacion": "0101",
                "Provincia": "AZUAY",
                "G1_Identificacion": "0202",
                "G1_Nombres": "GARANTE UNO",
            },
            "0002": {
                "NumeroPrestamo": "0002",
                "EstadoPrestamo": "VIGENTE",
            },
        }

    def obtener_corte_final(self, fecha_corte, fecha_actual, agencias, asesores):
        assert fecha_corte == date(2026, 9, 14)
        assert fecha_actual == date(2026, 9, 14)
        self.filtros = (agencias, asesores)
        return {
            "0001": {
                "NumeroPrestamo": "0001",
                "Agencia": "MATRIZ",
                "CodigoAsesor": "A01",
                "NombreAsesor": "ANA ASESORA",
                "EstadoPrestamo": "VIGENTE",
                "Calificacion": "A-3",
                "DiasVencidos": 3,
                "SaldoCapital": 900,
                "ProvisionRequerida": 45,
                "ValorParaEstarAlDia": 20,
                "ValorHastaCuotaActual": 120,
                "ValorCancelarTotal": 980,
                "GastoCobranza": 15,
                "Plazo": 12,
            },
            "0002": {
                "NumeroPrestamo": "0002",
                "Agencia": "MATRIZ",
                "NombreAsesor": "ANA ASESORA",
                "EstadoPrestamo": "CANCELADO",
            },
            "0003": {
                "NumeroPrestamo": "0003",
                "Agencia": "MATRIZ",
                "NombreAsesor": "ANA ASESORA",
                "EstadoPrestamo": "CANCELADO",
            },
        }

    def obtener_recuperaciones(
        self, fecha_inicio, fecha_fin, fecha_actual, numeros_prestamo
    ):
        assert set(numeros_prestamo) == {"0001", "0002"}
        return {
            "0001": RecuperacionPrestamo("0001", date(2026, 9, 10), 300),
            "0002": RecuperacionPrestamo("0002", date(2026, 9, 12), 1200),
        }


class FakeSqlRepository:
    def __init__(self) -> None:
        self.llamadas = 0
        self.payload = []

    def obtener_detalles(self, prestamos):
        self.llamadas += 1
        self.payload = prestamos
        return {
            "0001": DetalleCuotaPrestamo(
                numero_prestamo="0001",
                numero_cuota_actual_no_pagada=4,
                numero_cuota_siguiente=5,
                cobro_hasta_cuota=100,
                calificacion_con_cobro_una_cuota="A-2",
                dias_mora_con_cobro_una_cuota=0,
                saldo_capital_con_cobro_una_cuota=800,
                cuotas_pendientes=9,
                cuotas_pagadas=3,
                total_cuotas=12,
                porcentaje_minimo=1,
                porcentaje_maximo=10,
                es_porcentaje_fijo=False,
            )
        }


def test_schema_normaliza_agencias_y_asesores() -> None:
    entrada = InputRecaudacionAcumulada(
        fecha_inicio=date(2026, 9, 1),
        fecha_fin=date(2026, 9, 14),
        agencias=[" matriz ", "MATRIZ"],
        asesores=[" ana asesora ", "ANA ASESORA"],
    )
    assert entrada.agencias == ["MATRIZ"]
    assert entrada.asesores == ["ANA ASESORA"]


def test_schema_normaliza_ids_agencia() -> None:
    entrada = InputAsesoresPorAgencia(ids_agencia=[2, 2, 3])
    assert entrada.ids_agencia == [2, 3]


def test_endpoint_lista_asesores_por_agencia() -> None:
    class FakeAsesoresService:
        def listar(self, ids_agencia):
            assert ids_agencia == [2]
            return [
                AsesorAgenciaResponse(
                    codigo="A01",
                    nombre="ANA ASESORA",
                    id_agencia=2,
                    agencia="MATRIZ",
                    id_cargo=95,
                    cargo="ASESOR DE NEGOCIOS",
                )
            ]

    app.dependency_overrides[get_current_auth_context] = auth_context
    app.dependency_overrides[get_asesores_agencia_service] = FakeAsesoresService
    try:
        response = client.post(
            "/negocios/recuperacion/recaudacion-acumulada/asesores",
            json={"ids_agencia": [2]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {
            "codigo": "A01",
            "nombre": "ANA ASESORA",
            "id_agencia": 2,
            "agencia": "MATRIZ",
            "id_cargo": 95,
            "cargo": "ASESOR DE NEGOCIOS",
        }
    ]


def test_servicio_compone_mongo_y_una_sola_consulta_sql() -> None:
    mongo = FakeMongoRepository()
    sql = FakeSqlRepository()
    service = RecaudacionAcumuladaService(mongo, sql)  # type: ignore[arg-type]

    respuesta = service.obtener_recaudacion_acumulada(
        InputRecaudacionAcumulada(
            fecha_inicio=date(2026, 9, 1),
            fecha_fin=date(2026, 9, 14),
            agencias=["matriz"],
            asesores=["ana asesora"],
        ),
        auth_context(),
    )

    assert mongo.filtros == (["MATRIZ"], ["ANA ASESORA"])
    assert sql.llamadas == 1
    assert {fila["numero_prestamo"] for fila in sql.payload} == {"0001", "0002"}
    assert respuesta.total_registros == 2
    assert respuesta.total_recuperado == 1500
    assert [item.numero_prestamo for item in respuesta.prestamos] == ["0002", "0001"]
    prestamo = respuesta.prestamos[1]
    assert prestamo.variacion_dias_mora == -7
    assert prestamo.variacion_saldo_capital == -300
    assert prestamo.provision_cierre_mes == 120
    assert prestamo.provision_actual == 45
    assert prestamo.variacion_provisiones == -75
    assert prestamo.provision_con_cobro_una_cuota == 40
    assert prestamo.numero_cuota_siguiente == 5
    assert prestamo.cobro_para_bajar_una_cuota == 115
    assert prestamo.cuotas_pendientes == 9
    assert prestamo.saldo_capital_con_cobro_una_cuota == 800
    assert prestamo.pendiente_pago == 35
    assert prestamo.pendiente_pago_mas_cuota_por_vencer == 135
    assert prestamo.total_a_cancelar == 995
    assert prestamo.informacion_deudor.identificacion == "0101"  # type: ignore[union-attr]
    assert prestamo.garante_1.nombres == "GARANTE UNO"  # type: ignore[union-attr]
    assert respuesta.prestamos[0].informacion_deudor is None


def test_item_historico_sin_gasto_conserva_valores_base() -> None:
    item = RecaudacionAcumuladaService._construir_item(
        numero="0001",
        inicio={},
        fin={
            "NumeroPrestamo": "0001",
            "ValorParaEstarAlDia": 20,
            "ValorHastaCuotaActual": 120,
            "ValorCancelarTotal": 980,
        },
        detalle=DetalleCuotaPrestamo(
            numero_prestamo="0001",
            cobro_hasta_cuota=100,
        ),
        total_recuperado=0,
        fecha_ultimo_pago=None,
    )

    assert item.cobro_para_bajar_una_cuota == 100
    assert item.pendiente_pago == 20
    assert item.pendiente_pago_mas_cuota_por_vencer == 120
    assert item.total_a_cancelar == 980


def test_servicio_rechaza_fecha_futura() -> None:
    service = RecaudacionAcumuladaService(  # type: ignore[arg-type]
        FakeMongoRepository(), FakeSqlRepository()
    )
    with pytest.raises(HTTPException) as exc:
        service.obtener_recaudacion_acumulada(
            InputRecaudacionAcumulada(
                fecha_inicio=date(2026, 9, 1),
                fecha_fin=date(2026, 9, 15),
                agencias=["MATRIZ"],
            ),
            auth_context(),
        )
    assert exc.value.status_code == 400


def test_endpoint_usa_bearer_y_no_expone_paginacion() -> None:
    service = RecaudacionAcumuladaService(  # type: ignore[arg-type]
        FakeMongoRepository(), FakeSqlRepository()
    )
    app.dependency_overrides[get_current_auth_context] = auth_context
    app.dependency_overrides[get_recaudacion_acumulada_service] = lambda: service
    try:
        response = client.post(
            "/negocios/recuperacion/recaudacion-acumulada",
            json={
                "fecha_inicio": "2026-09-01",
                "fecha_fin": "2026-09-14",
                "agencias": ["MATRIZ"],
                "asesores": ["ANA ASESORA"],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "pagina" not in body
    assert body["total_registros"] == 2
    assert "codigo_usuario_cobranza_apoyo" not in body["prestamos"][0]
    assert "nombre_usuario_cobranza_apoyo" not in body["prestamos"][0]
    assert "numero_cuota_siguiente" in body["prestamos"][0]
    assert "cobro_para_bajar_una_cuota" in body["prestamos"][0]
    assert "cuotas_pendientes" in body["prestamos"][0]
    assert "saldo_capital_con_cobro_una_cuota" in body["prestamos"][0]
    assert "estado_prestamo" not in body["prestamos"][0]
    assert "dias_mora" not in body["prestamos"][0]
    assert "saldo_capital" not in body["prestamos"][0]
    assert "cobro_hasta_cuota" not in body["prestamos"][0]
    assert list(body["prestamos"][0]) == [
        "socio",
        "agencia",
        "numero_prestamo",
        "codigo_usuario_asignado",
        "nombre_usuario_asignado",
        "nombre",
        "estado_anterior",
        "estado_actual",
        "calificacion_anterior",
        "calificacion_actual",
        "dias_mora_anterior",
        "dias_mora_actual",
        "variacion_dias_mora",
        "saldo_capital_anterior",
        "saldo_capital_actual",
        "variacion_saldo_capital",
        "numero_cuota_actual_no_pagada",
        "numero_cuota_siguiente",
        "cobro_para_bajar_una_cuota",
        "cuotas_pendientes",
        "cuotas_pagadas",
        "total_cuotas",
        "calificacion_con_cobro_una_cuota",
        "dias_mora_con_cobro_una_cuota",
        "saldo_capital_con_cobro_una_cuota",
        "provision_con_cobro_una_cuota",
        "provision_cierre_mes",
        "provision_actual",
        "variacion_provisiones",
        "dia_ultimo_pago",
        "total_recuperado",
        "pendiente_pago",
        "pendiente_pago_mas_cuota_por_vencer",
        "total_a_cancelar",
        "informacion_deudor",
        "garante_1",
        "garante_2",
    ]


class FakeSqlResult:
    def mappings(self):
        return []


class FakeSession:
    def __init__(self) -> None:
        self.statement = ""
        self.parameters = {}
        self.llamadas = 0

    def execute(self, statement, parameters):
        self.llamadas += 1
        self.statement = str(statement)
        self.parameters = parameters
        return FakeSqlResult()


def test_repositorio_sql_envia_todo_el_universo_en_un_parametro_xml() -> None:
    session = FakeSession()
    repository = SqlDetalleCuotasRepository(session)  # type: ignore[arg-type]

    resultado = repository.obtener_detalles(
        [
            {"numero_prestamo": "0001", "provision_actual": 5, "saldo_actual": 100},
            {"numero_prestamo": "0002", "provision_actual": 7, "saldo_actual": 200},
        ]
    )

    assert resultado == {}
    assert session.llamadas == 1
    assert "Documento.nodes('/prestamos/prestamo')" in session.statement
    assert "ROUND(COALESCE(PR.CALCULADO, 0), 2)" in session.statement
    assert set(session.parameters) == {"prestamos_xml"}
    assert 'numero="0001"' in session.parameters["prestamos_xml"]
    assert 'numero="0002"' in session.parameters["prestamos_xml"]


def test_repositorio_sql_divide_universo_grande_en_lotes_paralelos(
    monkeypatch,
) -> None:
    tamanios: list[int] = []

    class RootSession:
        def get_bind(self):
            return object()

    class BoundSession:
        def __init__(self, *, bind):
            self.bind = bind

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    def fake_obtener_lote(self, prestamos):
        tamanios.append(len(prestamos))
        return {
            fila["numero_prestamo"]: DetalleCuotaPrestamo(
                numero_prestamo=fila["numero_prestamo"]
            )
            for fila in prestamos
        }

    monkeypatch.setattr(sql_repository_module, "Session", BoundSession)
    monkeypatch.setattr(
        SqlDetalleCuotasRepository,
        "_obtener_detalles_lote",
        fake_obtener_lote,
    )
    repository = SqlDetalleCuotasRepository(RootSession())  # type: ignore[arg-type]

    resultado = repository.obtener_detalles(
        [
            {
                "numero_prestamo": f"{indice:04d}",
                "provision_actual": 0,
                "saldo_actual": 0,
            }
            for indice in range(1201)
        ]
    )

    assert len(resultado) == 1201
    assert sorted(tamanios) == [201, 500, 500]

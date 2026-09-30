from datetime import datetime

from app.modules.negocios.cartera_de_credito.matriz_transicion.schemas import (
    MatrizTransicionPrestamosRequest,
    MatrizTransicionRequest,
)
from app.modules.negocios.cartera_de_credito.matriz_transicion.service import (
    MatrizTransicionService,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.domain import (
    DetalleCuotaPrestamo,
)


def _document(
    numero: str,
    identificador: int,
    calificacion: str,
    *,
    agencia: str = "CENTRO",
    asesor: str = "ASESOR-1",
    saldo: float = 100.0,
    provision: float = 10.0,
    diferido: bool = False,
    cancelado: bool = False,
    estado: str = "VIGENTE",
) -> dict:
    return {
        "NumeroPrestamo": numero,
        "IdPrestamo": identificador,
        "Calificacion": calificacion,
        "EstadoPrestamo": estado,
        "CodigoEstadoPrestamo": "V",
        "Agencia": agencia,
        "IdAgencia": 1 if agencia == "CENTRO" else 2,
        "CodigoAsesor": asesor,
        "NombreAsesor": "Asesor Uno",
        "CargoAsesor": "ASESOR DE NEGOCIOS",
        "EsDiferido": diferido,
        "EsCancelado": cancelado,
        "SaldoCapital": saldo,
        "ProvisionRequerida": provision,
        "ProvisionConstituida": provision / 2,
        "ExigibleCapital": 1.0,
        "ExigibleInteres": 2.0,
        "ExigibleMora": 3.0,
        "ExigibleOtros": 4.0,
        "ValorParaEstarAlDia": 5.0,
        "ValorHastaCuotaActual": 6.0,
        "ValorCancelarTotal": 7.0,
    }


class FakeMongoRepository:
    def __init__(self, historicos: dict[str, list[dict]], actuales: list[dict]) -> None:
        self.historicos = historicos
        self.actuales = actuales
        self.fechas_historicas: list[str] = []
        self.actual_consultado = False
        self.prestamos_anterior_solicitados: list[str] = []

    def obtener_historico_filtrado(self, fecha_corte: str, **_filtros: object) -> list[dict]:
        self.fechas_historicas.append(fecha_corte)
        return self.historicos.get(fecha_corte, [])

    def obtener_actual_filtrado(self, **_filtros: object) -> list[dict]:
        self.actual_consultado = True
        return self.actuales

    def obtener_anterior_por_prestamos(
        self,
        fecha_corte: str,
        numeros_prestamo: list[str],
    ) -> list[dict]:
        self.fechas_historicas.append(fecha_corte)
        self.prestamos_anterior_solicitados = numeros_prestamo
        return [
            document
            for document in self.historicos.get(fecha_corte, [])
            if document["NumeroPrestamo"] in numeros_prestamo
        ]


class FakeSqlDetalleCuotasRepository:
    def __init__(self) -> None:
        self.prestamos: list[dict] = []

    def obtener_detalles(self, prestamos: list[dict]) -> dict[str, DetalleCuotaPrestamo]:
        self.prestamos = prestamos
        return {
            prestamo["numero_prestamo"]: DetalleCuotaPrestamo(
                numero_prestamo=prestamo["numero_prestamo"],
                numero_cuota_actual_no_pagada=4,
                numero_cuota_siguiente=5,
                cobro_hasta_cuota=25,
                calificacion_con_cobro_una_cuota="A-1",
                dias_mora_con_cobro_una_cuota=0,
                saldo_capital_con_cobro_una_cuota=75,
                cuotas_pendientes=8,
                cuotas_pagadas=4,
                total_cuotas=12,
                porcentaje_fijo=2,
                es_porcentaje_fijo=True,
            )
            for prestamo in prestamos
        }


def _service(historicos: dict[str, list[dict]], actuales: list[dict]) -> tuple[MatrizTransicionService, FakeMongoRepository]:
    mongo = FakeMongoRepository(historicos, actuales)
    return MatrizTransicionService(mongo, FakeSqlDetalleCuotasRepository()), mongo


def _request(**overrides: object) -> MatrizTransicionRequest:
    values: dict[str, object] = {
        "fecha_corte_anterior": datetime(2026, 8, 31),
        "fecha_corte_nuevo": datetime(2026, 9, 30),
    }
    values.update(overrides)
    return MatrizTransicionRequest(**values)


def test_compara_cierre_mes_anterior_con_situacion_actual() -> None:
    historicos = {
        "20260831": [
            _document("100", 100, "A", saldo=100, provision=10),
            _document("300", 300, "B", saldo=25, cancelado=False),
        ]
    }
    actuales = [
        _document("100", 100, "B", saldo=120, provision=12),
        _document("200", 200, "C", saldo=50, provision=5),
        _document("300", 300, "C", saldo=10, cancelado=True),
    ]
    service, mongo = _service(historicos, actuales)

    response = service.obtener(_request(), hoy=datetime(2026, 9, 30).date())

    assert mongo.fechas_historicas == ["20260831"]
    assert mongo.prestamos_anterior_solicitados == ["100", "200", "300"]
    assert mongo.actual_consultado is True
    assert response.fecha_corte_anterior == "20260831"
    assert response.fecha_corte_nuevo == "20260930"
    assert response.fuente_corte_nuevo == "SituacionCrediticiaActual"
    assert response.categorias == ["A", "B", "C", "NA"]
    assert response.conteos["A"]["B"] == 1
    assert response.conteos["NA"]["C"] == 1
    assert response.conteos["B"]["C"] == 1
    assert response.saldos_capital["saldos_capital"]["A"]["B"] == 120
    assert response.saldos_capital["saldos_capital_variacion"]["A"]["B"] == 20
    assert response.saldos_capital["saldos_capital_variacion"]["B"]["C"] == -15


def test_usa_historico_cuando_el_corte_final_no_es_hoy() -> None:
    historicos = {
        "20260831": [_document("100", 100, "A")],
        "20260925": [_document("100", 100, "B")],
    }
    service, mongo = _service(historicos, [])

    response = service.obtener(
        _request(fecha_corte_nuevo=datetime(2026, 9, 25)),
        hoy=datetime(2026, 9, 30).date(),
    )

    assert mongo.fechas_historicas == ["20260925", "20260831"]
    assert mongo.actual_consultado is False
    assert response.fuente_corte_nuevo == "SituacionCrediticia"
    assert response.conteos["A"]["B"] == 1


def test_aplica_filtro_de_agencia_por_nombre_solo_al_corte_nuevo() -> None:
    historicos = {
        "20260831": [
            _document("100", 100, "A", agencia="CENTRO"),
            _document("200", 200, "A", agencia="NORTE"),
        ]
    }
    actuales = [
        _document("100", 100, "B", agencia="CENTRO"),
        _document("200", 200, "B", agencia="NORTE"),
    ]
    service, _ = _service(historicos, actuales)

    response = service.obtener(
        _request(Agencia=["CENTRO"]),
        hoy=datetime(2026, 9, 30).date(),
    )

    assert response.conteos["A"]["B"] == 1


def test_acepta_cortes_en_meses_distintos() -> None:
    historicos = {
        "20260930": [_document("100", 100, "A")],
        "20261001": [_document("100", 100, "B")],
    }
    service, mongo = _service(historicos, [])

    response = service.obtener(
        _request(
            fecha_corte_anterior=datetime(2026, 9, 30),
            fecha_corte_nuevo=datetime(2026, 10, 1),
        ),
        hoy=datetime(2026, 10, 2).date(),
    )

    assert mongo.fechas_historicas == ["20261001", "20260930"]
    assert response.conteos["A"]["B"] == 1


def test_descarta_solo_cancelados_del_corte_anterior() -> None:
    historicos = {
        "20260831": [
            _document("100", 100, "A", estado="CANCELADO", cancelado=True),
        ]
    }
    actuales = [_document("100", 100, "B", cancelado=True)]
    service, _ = _service(historicos, actuales)

    response = service.obtener(_request(), hoy=datetime(2026, 9, 30).date())

    assert response.conteos["NA"]["B"] == 1


def test_lista_prestamos_de_una_transicion_sin_paginado() -> None:
    historicos = {
        "20260831": [
            _document("100", 100, "A", saldo=100, provision=10),
            _document("200", 200, "B", saldo=50, provision=5),
        ]
    }
    actuales = [
        {
            **_document("100", 100, "B", saldo=120, provision=12),
            "Cliente": 77,
            "Nombres": "Socio de Prueba",
            "DiasVencidos": 6,
            "Plazo": 12,
            "ValorParaEstarAlDia": 30,
            "ValorHastaCuotaActual": 40,
            "ValorCancelarTotal": 120,
            "FechaUltimoPago": "2026-09-20",
        },
        _document("200", 200, "C", saldo=40, provision=4),
    ]
    service, mongo = _service(historicos, actuales)
    request = MatrizTransicionPrestamosRequest(
        fecha_corte_anterior=datetime(2026, 8, 31),
        fecha_corte_nuevo=datetime(2026, 9, 30),
        calificacion_anterior="A",
        calificacion_nueva="B",
    )

    prestamos = service.obtener_prestamos(request, hoy=datetime(2026, 9, 30).date())

    assert mongo.prestamos_anterior_solicitados == ["100", "200"]
    assert len(prestamos) == 1
    prestamo = prestamos[0]
    assert prestamo.numero_prestamo == "100"
    assert prestamo.calificacion_anterior == "A"
    assert prestamo.calificacion_actual == "B"
    assert prestamo.variacion_saldo_capital == 20
    assert prestamo.total_recuperado == 0
    assert prestamo.dia_ultimo_pago.isoformat() == "2026-09-20"
    assert prestamo.numero_cuota_actual_no_pagada == 4
    assert prestamo.numero_cuota_siguiente == 5
    assert prestamo.cobro_para_bajar_una_cuota == 25
    assert prestamo.cuotas_pendientes == 8

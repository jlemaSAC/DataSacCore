from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.cartera_de_credito.cartera_improductiva.dependencies import (
    get_cartera_improductiva_service,
)
from app.modules.negocios.cartera_de_credito.cartera_improductiva.service import (
    CarteraImproductivaService,
    _mes_anterior,
)
from app.modules.negocios.router import router as negocios_router


def _document(
    numero: str,
    codigo: str,
    *,
    nombre: str,
    saldo: float,
    no_devenga: float,
    vencido: float,
    agencia: str = "CENTRO",
    diferido: bool = False,
) -> dict:
    return {
        "NumeroPrestamo": numero,
        "CodigoUsuario": codigo,
        "NombreAsesor": nombre,
        "CargoAsesor": "ASESOR DE NEGOCIOS",
        "Agencia": agencia,
        "Cliente": numero,
        "SaldoCapital": saldo,
        "CapitalNoDevenga": no_devenga,
        "CapitalVencido": vencido,
        "ProvisionRequerida": 0,
        "EstadoPrestamo": "VIGENTE",
        "EsDiferido": diferido,
    }


class FakeMongoRepository:
    def __init__(self) -> None:
        self.actuales = [
            _document(
                "1",
                "ASESOR_ACTUAL",
                nombre="Asesor actual",
                saldo=100,
                no_devenga=10,
                vencido=5,
            ),
            _document(
                "2",
                "SOLO_FIN",
                nombre="Solo final",
                saldo=50,
                no_devenga=2,
                vencido=3,
            ),
        ]
        self.historicos = {
            "20260820": [
                _document("1", "ASESOR_ANTERIOR", nombre="Asesor anterior", saldo=80, no_devenga=8, vencido=0)
            ],
            "20260823": [
                _document("1", "ASESOR_ANTERIOR", nombre="Asesor anterior", saldo=100, no_devenga=12, vencido=0)
            ],
            "20260920": [
                _document(
                    "1",
                    "ASESOR_ANTERIOR",
                    nombre="Asesor anterior",
                    saldo=50,
                    no_devenga=4,
                    vencido=6,
                )
            ],
            "20260922": [
                _document(
                    "1",
                    "ASESOR_ANTERIOR",
                    nombre="Asesor anterior",
                    saldo=40,
                    no_devenga=2,
                    vencido=2,
                )
            ],
        }

    def obtener_ultimo_corte_actual(self) -> str:
        return "20260923"

    def obtener_actual(
        self,
        fecha_corte: str,
        agencia_nombre: str | None,
    ) -> list[dict]:
        assert fecha_corte == "20260923"
        assert agencia_nombre is None
        return self.actuales

    def obtener_historico(
        self,
        fecha_corte: str,
        agencia_nombre: str | None,
    ) -> list[dict]:
        assert agencia_nombre is None
        return self.historicos.get(fecha_corte, [])


class FakeSqlRepository:
    def obtener_nombre_agencia(self, id_agencia: int) -> str | None:
        return "CENTRO" if id_agencia == 1 else None

    def obtener_gerentes_oficina(self, agencias: list[str]) -> list[dict]:
        assert agencias == ["CENTRO"]
        return [
            {
                "IdAgencia": 1,
                "Agencia": "CENTRO",
                "CodigoUsuarioGerente": "GERENTE",
                "GerenteOficina": "Gerente de oficina",
                "Cargo": "GERENTE DE OFICINA",
            }
        ]


def _service() -> CarteraImproductivaService:
    return CarteraImproductivaService(FakeMongoRepository(), FakeSqlRepository())


def test_mes_anterior_ajusta_fin_de_mes_y_cambio_de_anio() -> None:
    assert _mes_anterior(date(2026, 3, 31)) == date(2026, 2, 28)
    assert _mes_anterior(date(2024, 3, 31)) == date(2024, 2, 29)
    assert _mes_anterior(date(2026, 1, 15)) == date(2025, 12, 15)


def test_incluye_asesor_y_prestamo_presentes_solo_en_mes_anterior() -> None:
    mongo = FakeMongoRepository()
    mongo.historicos["20260820"].append(
        _document("9", "SOLO_PREVIO", nombre="Asesor previo", saldo=100, no_devenga=5, vencido=0)
    )
    mongo.historicos["20260823"].append(
        _document("9", "SOLO_PREVIO", nombre="Asesor previo", saldo=100, no_devenga=9, vencido=0)
    )
    service = CarteraImproductivaService(mongo, FakeSqlRepository())
    response = service.obtener(fecha_inicio=date(2026, 9, 20), fecha_fin=date(2026, 9, 23))
    previo = next(item for item in response.comparacion if item.codigo_usuario == "SOLO_PREVIO")
    assert previo.valores_fecha_fin is None
    assert previo.nombre_asesor_fecha_fin_mes_anterior == "Asesor previo"
    assert previo.valores_fecha_fin_mes_anterior.cartera_improductiva == 9

    detalle = service.obtener_prestamos(_detalle_request(
        grupos=[{"codigo_usuario": "SOLO_PREVIO", "agencia": "CENTRO"}],
    ))
    assert [item.numero_prestamo for item in detalle.prestamos] == ["9"]
    assert detalle.totales.valores_fecha_inicio_mes_anterior.cartera_improductiva == 5
    assert detalle.totales.valores_fecha_fin_mes_anterior.cartera_improductiva == 9


def test_service_compara_los_tres_cortes_y_reasigna_al_asesor_actual() -> None:
    response = _service().obtener(
        fecha_inicio=date(2026, 9, 20),
        fecha_fin=date(2026, 9, 23),
    )

    assert response.fecha_corte_fecha_fin == "20260923"
    assert response.fecha_corte_fecha_inicio == "20260920"
    assert response.fecha_corte_dia_anterior_fecha_fin == "20260922"
    assert response.fecha_corte_fecha_inicio_mes_anterior == "20260820"
    assert response.fecha_corte_fecha_fin_mes_anterior == "20260823"
    assert [item.codigo_usuario for item in response.comparacion] == [
        "ASESOR_ACTUAL",
        "SOLO_FIN",
    ]

    asesor = response.comparacion[0]
    assert asesor.nombre_asesor_fecha_fin == "Asesor actual"
    assert asesor.nombre_asesor_fecha_inicio == "Asesor anterior"
    assert asesor.valores_fecha_fin is not None
    assert asesor.valores_fecha_fin.saldo_capital == 100
    assert asesor.valores_fecha_fin.cartera_improductiva == 15
    assert asesor.valores_fecha_fin.morosidad == 0.15
    assert asesor.valores_fecha_inicio is not None
    assert asesor.valores_fecha_inicio.saldo_capital == 50
    assert asesor.valores_fecha_inicio.cartera_improductiva == 10
    assert asesor.valores_fecha_inicio.morosidad_porcentaje == 20
    assert asesor.valores_dia_anterior_fecha_fin is not None
    assert asesor.valores_dia_anterior_fecha_fin.saldo_capital == 40
    assert asesor.valores_dia_anterior_fecha_fin.cartera_improductiva == 4
    assert asesor.valores_fecha_inicio_mes_anterior.cartera_improductiva == 8
    assert asesor.valores_fecha_fin_mes_anterior.cartera_improductiva == 12
    assert response.faltantes_en_fecha_inicio == ["SOLO_FIN"]
    assert response.faltantes_en_dia_anterior_fecha_fin == ["SOLO_FIN"]
    assert response.agencias_gerentes_oficina[0].codigo_usuario_gerente == "GERENTE"


def test_service_aplica_el_filtro_de_diferidos_en_los_tres_cortes() -> None:
    mongo_repository = FakeMongoRepository()
    mongo_repository.actuales[1]["EsDiferido"] = True
    service = CarteraImproductivaService(mongo_repository, FakeSqlRepository())

    response = service.obtener(
        fecha_inicio=date(2026, 9, 20),
        fecha_fin=date(2026, 9, 23),
        filtrar_diferidos=False,
    )

    assert [item.codigo_usuario for item in response.comparacion] == ["ASESOR_ACTUAL"]
    assert response.faltantes_en_fecha_inicio == []
    assert response.faltantes_en_dia_anterior_fecha_fin == []


def test_service_permite_rangos_que_cruzan_meses() -> None:
    mongo_repository = FakeMongoRepository()
    mongo_repository.historicos["20260831"] = mongo_repository.historicos["20260920"]
    service = CarteraImproductivaService(mongo_repository, FakeSqlRepository())

    response = service.obtener(
        fecha_inicio=date(2026, 8, 31),
        fecha_fin=date(2026, 9, 23),
    )

    assert response.fecha_corte_fecha_inicio == "20260831"
    assert response.fecha_corte_dia_anterior_fecha_fin == "20260922"


def test_endpoint_expone_el_contrato_con_los_aliases() -> None:
    app = FastAPI()
    app.include_router(negocios_router)
    app.dependency_overrides[get_current_auth_context] = lambda: AuthContext(
        usuario=UsuarioTokenPayload(
            sub="ASESOR",
            usuario="ASESOR",
            id_agencia=1,
            fecha_sistema=date(2026, 9, 23),
        ),
        token="token",
    )
    app.dependency_overrides[get_cartera_improductiva_service] = _service

    with TestClient(app) as client:
        response = client.post(
            "/negocios/cartera-de-credito/cartera-improductiva",
            json={
                "fecha_inicio": "2026-09-20",
                "fecha_fin": "2026-09-23",
                "id_agencia": 0,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["fecha_corte_fecha_fin"] == "20260923"
    assert body["comparacion"][0]["ValoresFechaFin"] == {
        "SaldoCapital": 100.0,
        "CarteraImproductiva": 15.0,
        "Morosidad": 0.15,
        "MorosidadPorcentaje": 15.0,
    }


def test_service_filtra_la_agencia_en_los_tres_cortes() -> None:
    class MongoPorAgencia(FakeMongoRepository):
        def obtener_actual(self, fecha_corte, agencia_nombre):
            assert fecha_corte == "20260923"
            assert agencia_nombre == "CENTRO"
            return [item for item in self.actuales if item["Agencia"] == agencia_nombre]

        def obtener_historico(self, fecha_corte, agencia_nombre):
            assert agencia_nombre == "CENTRO"
            return [
                item for item in self.historicos.get(fecha_corte, [])
                if item["Agencia"] == agencia_nombre
            ]

    mongo = MongoPorAgencia()
    otra_agencia = _document(
        "3", "OTRO", nombre="Otro asesor", saldo=900,
        no_devenga=0, vencido=0, agencia="QUITO",
    )
    mongo.actuales.append(otra_agencia)
    for documentos in mongo.historicos.values():
        documentos.append(otra_agencia)
    service = CarteraImproductivaService(mongo, FakeSqlRepository())

    response = service.obtener(
        fecha_inicio=date(2026, 9, 20),
        fecha_fin=date(2026, 9, 23),
        id_agencia=1,
    )

    assert [item.codigo_usuario for item in response.comparacion] == [
        "ASESOR_ACTUAL", "SOLO_FIN",
    ]
    assert sum(item.valores_fecha_fin.saldo_capital for item in response.comparacion) == 150
    assert response.comparacion[0].valores_fecha_inicio.saldo_capital == 50
    assert response.comparacion[0].valores_dia_anterior_fecha_fin.saldo_capital == 40


class FakeClientesRepository:
    def __init__(self) -> None:
        self.consultas: list[list[str]] = []

    def obtener_clientes(self, numeros: list[str]) -> dict[str, dict[str, str]]:
        self.consultas.append(numeros)
        return {numero: {"NombreCliente": f"Cliente {numero}", "NumeroSocio": f"S{numero}"} for numero in numeros}


def _detalle_request(**cambios):
    from app.modules.negocios.cartera_de_credito.cartera_improductiva.schemas import (
        CarteraImproductivaPrestamosRequest,
    )
    return CarteraImproductivaPrestamosRequest.model_validate({
        "fecha_inicio": "2026-09-20", "fecha_fin": "2026-09-23",
        "grupos": [{"codigo_usuario": "ASESOR_ACTUAL", "agencia": "CENTRO"}],
        **cambios,
    })


def test_detalle_une_por_numero_y_reasigna_sin_reemplazar_importes_historicos():
    clientes = FakeClientesRepository()
    service = CarteraImproductivaService(FakeMongoRepository(), FakeSqlRepository(), clientes)
    response = service.obtener_prestamos(_detalle_request())
    assert response.total_seleccion == response.total_resultados == 1
    prestamo = response.prestamos[0]
    assert prestamo.numero_prestamo == "1"
    assert prestamo.codigo_usuario == "ASESOR_ACTUAL"
    assert prestamo.nombre_cliente == "Cliente 1"
    assert prestamo.nombre_asesor_fecha_inicio == "Asesor anterior"
    assert prestamo.valores_fecha_inicio.cartera_improductiva == 10
    assert prestamo.valores_dia_anterior_fecha_fin.cartera_improductiva == 4
    assert prestamo.valores_fecha_fin.cartera_improductiva == 15
    assert prestamo.valores_fecha_inicio_mes_anterior.cartera_improductiva == 8
    assert prestamo.valores_fecha_fin_mes_anterior.cartera_improductiva == 12
    principal = service.obtener(fecha_inicio=date(2026, 9, 20), fecha_fin=date(2026, 9, 23))
    assert response.totales.valores_fecha_inicio == principal.comparacion[0].valores_fecha_inicio
    assert response.totales.valores_fecha_fin == principal.comparacion[0].valores_fecha_fin
    assert clientes.consultas == [["1"]]


def test_detalle_incluye_prestamos_ausentes_en_cualquiera_de_los_tres_cortes():
    mongo = FakeMongoRepository()
    mongo.historicos["20260920"].append(_document(
        "3", "SOLO_INICIO", nombre="Solo inicio", saldo=100, no_devenga=20, vencido=0,
    ))
    mongo.historicos["20260922"].append(_document(
        "4", "SOLO_ANTERIOR", nombre="Solo anterior", saldo=90, no_devenga=0, vencido=9,
    ))
    service = CarteraImproductivaService(mongo, FakeSqlRepository())
    grupos = [{"codigo_usuario": codigo, "agencia": "CENTRO"} for codigo in (
        "ASESOR_ACTUAL", "SOLO_FIN", "SOLO_INICIO", "SOLO_ANTERIOR",
    )]
    response = service.obtener_prestamos(_detalle_request(grupos=grupos))
    por_numero = {item.numero_prestamo: item for item in response.prestamos}
    assert set(por_numero) == {"1", "2", "3", "4"}
    assert por_numero["2"].valores_fecha_inicio is None
    assert por_numero["3"].valores_fecha_fin is None
    assert por_numero["3"].codigo_usuario == "SOLO_INICIO"
    assert por_numero["4"].valores_fecha_fin is None
    assert por_numero["4"].valores_fecha_inicio is None
    assert response.totales.valores_fecha_fin.cartera_improductiva == 20
    assert response.totales.valores_fecha_inicio.cartera_improductiva == 30
    assert response.totales.valores_dia_anterior_fecha_fin.cartera_improductiva == 13


def test_detalle_preserva_la_agencia_de_cada_corte_y_no_duplica_sus_importes():
    mongo = FakeMongoRepository()
    mongo.actuales[0]["Agencia"] = "QUITO"
    service = CarteraImproductivaService(mongo, FakeSqlRepository())
    centro = service.obtener_prestamos(_detalle_request())
    quito = service.obtener_prestamos(_detalle_request(
        grupos=[{"codigo_usuario": "ASESOR_ACTUAL", "agencia": "QUITO"}],
    ))
    assert centro.prestamos[0].valores_fecha_fin is None
    assert centro.prestamos[0].valores_fecha_inicio.cartera_improductiva == 10
    assert quito.prestamos[0].valores_fecha_inicio is None
    assert quito.prestamos[0].valores_fecha_fin.cartera_improductiva == 15
    todas = service.obtener_prestamos(_detalle_request(grupos=[
        {"codigo_usuario": "ASESOR_ACTUAL", "agencia": "CENTRO"},
        {"codigo_usuario": "ASESOR_ACTUAL", "agencia": "QUITO"},
    ]))
    assert todas.total_seleccion == 1
    assert todas.prestamos[0].valores_fecha_inicio.cartera_improductiva == 10
    assert todas.prestamos[0].valores_fecha_fin.cartera_improductiva == 15


def test_detalle_reasigna_antes_de_filtrar_diferidos_y_distingue_ceros_de_ausencias():
    mongo = FakeMongoRepository()
    mongo.actuales[0]["EsDiferido"] = True
    mongo.historicos["20260922"][0]["CapitalNoDevenga"] = 0
    mongo.historicos["20260922"][0]["CapitalVencido"] = 0
    service = CarteraImproductivaService(mongo, FakeSqlRepository())
    response = service.obtener_prestamos(_detalle_request(filtrar_diferidos=False))
    prestamo = response.prestamos[0]
    assert prestamo.codigo_usuario == "ASESOR_ACTUAL"
    assert prestamo.valores_fecha_fin is None
    assert prestamo.valores_dia_anterior_fecha_fin.cartera_improductiva == 0
    assert prestamo.valores_fecha_inicio.cartera_improductiva == 10


def test_detalle_devuelve_todos_los_prestamos_y_conserva_el_filtro_y_los_totales():
    mongo = FakeMongoRepository()
    mongo.actuales.extend(
        _document(str(numero), "ASESOR_ACTUAL", nombre="Asesor actual",
                  saldo=100, no_devenga=0, vencido=0)
        for numero in range(3, 254)
    )
    clientes = FakeClientesRepository()
    service = CarteraImproductivaService(mongo, FakeSqlRepository(), clientes)
    response = service.obtener_prestamos(_detalle_request())
    assert response.total_resultados == response.total_seleccion == 252
    assert len(response.prestamos) == 252
    assert response.prestamos[0].numero_prestamo == "1"
    assert all(item.nombre_cliente for item in response.prestamos)
    assert len(clientes.consultas[0]) == 252
    assert response.totales.valores_fecha_fin.saldo_capital == 25200
    filtrado = service.obtener_prestamos(_detalle_request(solo_improductivos=True))
    assert filtrado.total_seleccion == 252
    assert filtrado.total_resultados == len(filtrado.prestamos) == 1
    assert filtrado.totales == response.totales
    assert filtrado.prestamos[0].numero_prestamo == "1"


def test_detalle_rechaza_grupos_desactualizados_y_datos_sin_numero():
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        _service().obtener_prestamos(_detalle_request(grupos=[{"codigo_usuario": "INEXISTENTE"}]))
    assert error.value.status_code == 409
    mongo = FakeMongoRepository()
    mongo.actuales[0]["NumeroPrestamo"] = None
    with pytest.raises(HTTPException) as error:
        CarteraImproductivaService(mongo, FakeSqlRepository()).obtener_prestamos(_detalle_request())
    assert error.value.status_code == 409


def test_endpoint_detalle_con_bearer_valida_y_expone_los_tres_cortes():
    app = FastAPI()
    app.include_router(negocios_router)
    app.dependency_overrides[get_cartera_improductiva_service] = _service
    path = "/negocios/cartera-de-credito/cartera-improductiva/prestamos"
    body = _detalle_request().model_dump(mode="json")
    with TestClient(app) as client:
        assert client.post(path, json=body).status_code in {401, 403}
        app.dependency_overrides[get_current_auth_context] = lambda: AuthContext(
            usuario=UsuarioTokenPayload(sub="ASESOR", usuario="ASESOR", id_agencia=1, fecha_sistema=date(2026, 9, 23)), token="token",
        )
        response = client.post(path, json=body)
        assert response.status_code == 200
        resultado = response.json()
        assert resultado["prestamos"][0]["NumeroPrestamo"] == "1"
        assert resultado["prestamos"][0]["ValoresFechaInicio"]["CarteraImproductiva"] == 10
        assert resultado["totales"]["ValoresFechaFin"]["CarteraImproductiva"] == 15
        assert "pagina" not in resultado
        assert "tamano_pagina" not in resultado
        for cambios in ({"grupos": []}, {"orden_por": "campo_invalido"}):
            assert client.post(path, json={**body, **cambios}).status_code == 422
        assert client.post(path, json={**body, "fecha_inicio": "2026-10-01"}).status_code == 400


def test_detalle_usa_el_asesor_de_fecha_fin_historica_y_no_el_operativo_actual():
    mongo = FakeMongoRepository()
    mongo.historicos["20260921"] = mongo.historicos["20260920"]
    service = CarteraImproductivaService(mongo, FakeSqlRepository())
    response = service.obtener_prestamos(_detalle_request(
        fecha_fin="2026-09-22",
        grupos=[{"codigo_usuario": "ASESOR_ANTERIOR", "agencia": "CENTRO"}],
    ))
    assert response.fecha_corte_fecha_fin == "20260922"
    assert response.prestamos[0].codigo_usuario == "ASESOR_ANTERIOR"
    assert response.prestamos[0].valores_fecha_fin.cartera_improductiva == 4
    assert response.prestamos[0].valores_fecha_inicio.cartera_improductiva == 10


def test_detalle_limita_la_consulta_a_una_agencia_y_valida_su_existencia():
    import pytest
    from fastapi import HTTPException
    class MongoAgencia(FakeMongoRepository):
        def obtener_actual(self, fecha_corte, agencia_nombre):
            assert agencia_nombre == "CENTRO"
            return [doc for doc in self.actuales if doc["Agencia"] == agencia_nombre]

        def obtener_historico(self, fecha_corte, agencia_nombre):
            assert agencia_nombre == "CENTRO"
            return [doc for doc in self.historicos.get(fecha_corte, []) if doc["Agencia"] == agencia_nombre]

    mongo = MongoAgencia()
    mongo.actuales.append(_document("9", "ASESOR_ACTUAL", nombre="Otro", saldo=900, no_devenga=900, vencido=0, agencia="QUITO"))
    service = CarteraImproductivaService(mongo, FakeSqlRepository())
    response = service.obtener_prestamos(_detalle_request(id_agencia=1))
    assert response.total_seleccion == 1
    assert response.totales.valores_fecha_fin.cartera_improductiva == 15
    with pytest.raises(HTTPException) as error:
        service.obtener_prestamos(_detalle_request(id_agencia=999))
    assert error.value.status_code == 404


def test_detalle_ordena_todos_los_prestamos_y_deja_ausencias_al_final():
    mongo = FakeMongoRepository()
    mongo.historicos["20260920"].append(_document("3", "ASESOR_ACTUAL", nombre="Asesor", saldo=100, no_devenga=30, vencido=0))
    mongo.actuales.append(_document("4", "ASESOR_ACTUAL", nombre="Asesor", saldo=100, no_devenga=60, vencido=0))
    service = CarteraImproductivaService(mongo, FakeSqlRepository())
    asc = service.obtener_prestamos(_detalle_request(orden=1))
    desc = service.obtener_prestamos(_detalle_request(orden=-1))
    assert [item.numero_prestamo for item in asc.prestamos] == ["1", "4", "3"]
    assert [item.numero_prestamo for item in desc.prestamos] == ["4", "1", "3"]

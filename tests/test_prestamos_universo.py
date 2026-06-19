from datetime import datetime

from app.modules.prestamos.filtros import (
    build_mongo_match_actual,
    build_mongo_match_historico,
    filtros_hash,
    normalizar_universe_request,
)
from app.modules.prestamos.metricas import (
    calcular_capital_vigente,
    calcular_cartera_improductiva,
    calcular_mora,
    diferencia_metricas,
    sumar_metricas_cartera,
)
from app.modules.prestamos.normalizadores import (
    es_diferido,
    normalizar_codigo_usuario,
    normalizar_numero_prestamo,
    normalizar_texto,
    to_float_safe,
    to_int_safe,
)
from app.modules.prestamos.schemas import CarteraMetricas, PrestamoSnapshot, PrestamoUniverseRequest


def test_normalizadores_limpian_texto_codigos_y_numeros() -> None:
    assert normalizar_texto("  asesor   de negocios  ") == "ASESOR DE NEGOCIOS"
    assert normalizar_codigo_usuario(" jperez ") == "JPEREZ"
    assert normalizar_numero_prestamo(123.0) == "123"
    assert normalizar_numero_prestamo(" 000123 ") == "000123"


def test_normalizadores_convierten_numeros_y_diferidos() -> None:
    assert to_float_safe("1,234.56") == 1234.56
    assert to_float_safe("1.234,56") == 1234.56
    assert to_float_safe(None) == 0.0
    assert to_int_safe("12.9") == 12
    assert es_diferido("SI") is True
    assert es_diferido("Diferido") is True
    assert es_diferido("NO") is False
    assert es_diferido(None) is False


def test_normalizar_universe_request_deduplica_y_normaliza_listas() -> None:
    filtros = normalizar_universe_request(
        {
            "ids_prestamo": ["1", 1, "2"],
            "numeros_prestamo": [" 0001 ", "0001", 2.0],
            "agencia_nombres": [" matriz ", "MATRIZ"],
            "codigos_asesor": [" jperez ", "JPEREZ", "mlopez"],
            "calificaciones": [" a-1 ", "A-1"],
            "productos": [" microcredito ", "MICROCREDITO"],
        }
    )

    assert filtros.ids_prestamo == [1, 2]
    assert filtros.numeros_prestamo == ["0001", "2"]
    assert filtros.agencia_nombres == ["MATRIZ"]
    assert filtros.codigos_asesor == ["JPEREZ", "MLOPEZ"]
    assert filtros.calificaciones == ["A-1"]
    assert filtros.productos == ["MICROCREDITO"]


def test_build_mongo_match_actual_usa_campos_canonicos_y_aliases() -> None:
    filtros = PrestamoUniverseRequest(
        ids_prestamo=[10],
        agencias=[2],
        codigos_asesor=["jperez"],
        codigos_usuario_control=["mlopez"],
        estados_prestamo=["vigente"],
        filtrar_diferidos=False,
    )

    match = build_mongo_match_actual(filtros)

    assert match["IdPrestamo"] == {"$in": [10]}
    assert match["IdAgencia"] == {"$in": [2]}
    assert match["CodigoAsesor"] == {"$in": ["JPEREZ"]}
    assert {
        "$or": [
            {"CodigoUsuarioControl": {"$in": ["MLOPEZ"]}},
            {"CodigoUsuarioResponsableControl": {"$in": ["MLOPEZ"]}},
        ]
    } in match["$and"]
    assert {
        "$or": [
            {"EstadoPrestamo": {"$in": ["VIGENTE"]}},
            {"CodigoEstadoPrestamo": {"$in": ["VIGENTE"]}},
            {"CodigoEstado": {"$in": ["VIGENTE"]}},
        ]
    } in match["$and"]
    assert {"$or": [{"EsDiferido": False}, {"ESDIFERIDO": False}, {"Diferido": False}]} in match["$and"]


def test_build_mongo_match_historico_agrega_fecha_corte_y_excluye_cancelados_por_default() -> None:
    match = build_mongo_match_historico(
        PrestamoUniverseRequest(fecha_corte_anterior=datetime(2026, 5, 31), agencia_nombres=["centro"])
    )

    assert match["fecha_corte"] == "20260531"
    assert match["Agencia"] == {"$in": ["CENTRO"]}
    assert {
        "$and": [
            {"EstadoPrestamo": {"$nin": ["CANCELADO", "C"]}},
            {"CodigoEstadoPrestamo": {"$ne": "C"}},
            {"CodigoEstado": {"$ne": "C"}},
        ]
    } in match["$and"]


def test_filtros_hash_es_estable_para_filtros_equivalentes() -> None:
    primer_hash = filtros_hash({"codigos_asesor": [" jperez ", "JPEREZ"], "agencias": ["1"]})
    segundo_hash = filtros_hash({"codigos_asesor": ["JPEREZ"], "agencias": [1]})

    assert primer_hash == segundo_hash


def test_metricas_calculan_cartera_mora_suma_y_diferencia() -> None:
    snapshot = PrestamoSnapshot(
        numero_prestamo="0001",
        saldo_capital=1000,
        capital_no_devenga=100,
        capital_vencido=50,
        provision_requerida=30,
        provision_constituida=20,
    )

    total = sumar_metricas_cartera([snapshot])
    diferencia = diferencia_metricas(
        actual=total,
        historico=CarteraMetricas(
            operaciones=1,
            saldo_capital=900,
            capital_vigente=800,
            capital_no_devenga=80,
            capital_vencido=20,
            cartera_improductiva=100,
            mora=100 / 900,
            mora_porcentaje=(100 / 900) * 100,
            provision_requerida=25,
            provision_constituida=15,
        ),
    )

    assert calcular_cartera_improductiva(100, 50) == 150
    assert calcular_capital_vigente(1000, 100, 50) == 850
    assert calcular_mora(1000, 100, 50) == 0.15
    assert total.operaciones == 1
    assert total.capital_vigente == 850
    assert total.cartera_improductiva == 150
    assert total.mora_porcentaje == 15
    assert diferencia.saldo_capital == 100
    assert diferencia.provision_requerida == 5

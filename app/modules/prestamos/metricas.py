from collections.abc import Iterable

from app.modules.prestamos.normalizadores import to_float_safe
from app.modules.prestamos.schemas import CarteraMetricas, PrestamoSnapshot


def calcular_cartera_improductiva(capital_no_devenga: float, capital_vencido: float) -> float:
    return to_float_safe(capital_no_devenga) + to_float_safe(capital_vencido)


def calcular_capital_vigente(
    saldo_capital: float,
    capital_no_devenga: float,
    capital_vencido: float,
) -> float:
    return max(
        to_float_safe(saldo_capital) - calcular_cartera_improductiva(capital_no_devenga, capital_vencido),
        0.0,
    )


def calcular_mora(saldo_capital: float, capital_no_devenga: float, capital_vencido: float) -> float:
    saldo = to_float_safe(saldo_capital)
    if saldo == 0:
        return 0.0
    return calcular_cartera_improductiva(capital_no_devenga, capital_vencido) / saldo


def metricas_desde_snapshot(snapshot: PrestamoSnapshot) -> CarteraMetricas:
    cartera_improductiva = calcular_cartera_improductiva(
        snapshot.capital_no_devenga,
        snapshot.capital_vencido,
    )
    mora = calcular_mora(snapshot.saldo_capital, snapshot.capital_no_devenga, snapshot.capital_vencido)

    return CarteraMetricas(
        operaciones=1,
        saldo_capital=snapshot.saldo_capital,
        capital_vigente=snapshot.capital_vigente
        or calcular_capital_vigente(
            snapshot.saldo_capital,
            snapshot.capital_no_devenga,
            snapshot.capital_vencido,
        ),
        capital_no_devenga=snapshot.capital_no_devenga,
        capital_vencido=snapshot.capital_vencido,
        cartera_improductiva=cartera_improductiva,
        mora=mora,
        mora_porcentaje=mora * 100,
        provision_requerida=snapshot.provision_requerida,
        provision_constituida=snapshot.provision_constituida,
    )


def sumar_metricas_cartera(items: Iterable[CarteraMetricas | PrestamoSnapshot]) -> CarteraMetricas:
    total = CarteraMetricas()
    for item in items:
        metricas = metricas_desde_snapshot(item) if isinstance(item, PrestamoSnapshot) else item
        total.operaciones += metricas.operaciones
        total.saldo_capital += metricas.saldo_capital
        total.capital_vigente += metricas.capital_vigente
        total.capital_no_devenga += metricas.capital_no_devenga
        total.capital_vencido += metricas.capital_vencido
        total.provision_requerida += metricas.provision_requerida
        total.provision_constituida += metricas.provision_constituida

    total.cartera_improductiva = calcular_cartera_improductiva(total.capital_no_devenga, total.capital_vencido)
    total.mora = calcular_mora(total.saldo_capital, total.capital_no_devenga, total.capital_vencido)
    total.mora_porcentaje = total.mora * 100
    return total


def diferencia_metricas(actual: CarteraMetricas, historico: CarteraMetricas) -> CarteraMetricas:
    cartera_improductiva = actual.cartera_improductiva - historico.cartera_improductiva
    mora = actual.mora - historico.mora

    return CarteraMetricas(
        operaciones=actual.operaciones - historico.operaciones,
        saldo_capital=actual.saldo_capital - historico.saldo_capital,
        capital_vigente=actual.capital_vigente - historico.capital_vigente,
        capital_no_devenga=actual.capital_no_devenga - historico.capital_no_devenga,
        capital_vencido=actual.capital_vencido - historico.capital_vencido,
        cartera_improductiva=cartera_improductiva,
        mora=mora,
        mora_porcentaje=mora * 100,
        provision_requerida=actual.provision_requerida - historico.provision_requerida,
        provision_constituida=actual.provision_constituida - historico.provision_constituida,
    )


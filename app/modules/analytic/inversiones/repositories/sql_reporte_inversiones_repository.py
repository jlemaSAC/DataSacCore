from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.analytic.inversiones.constants import REPORTE_INVERSIONES_SP


class SqlReporteInversionesRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_corte_actual(self, fecha_corte: date) -> list[dict[str, Any]]:
        result = self.db.execute(
            text(
                f"""
                SET NOCOUNT ON;
                EXEC {REPORTE_INVERSIONES_SP}
                    @FechaDesde = :fecha_corte,
                    @FechaHasta = :fecha_corte;
                """
            ),
            {"fecha_corte": fecha_corte},
        )
        if not result.returns_rows:
            raise RuntimeError("El SP de inversiones no devolvió columnas.")

        filas: list[dict[str, Any]] = []
        for row in result.mappings().all():
            fila = dict(row)
            fila["tipo_prestamo"] = _lista_desde_separador(
                fila.pop("tipo_prestamo_lista", None)
            )
            fila["producto"] = _lista_desde_separador(fila.pop("producto_lista", None))
            filas.append(fila)
        return filas


def _lista_desde_separador(value: Any) -> list[str]:
    if not value:
        return []

    return [elemento.strip() for elemento in str(value).split("\u200b") if elemento.strip()]

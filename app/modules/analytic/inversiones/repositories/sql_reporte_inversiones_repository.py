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
        return [dict(row) for row in result.mappings().all()]

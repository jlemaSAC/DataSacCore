from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.analytic.ahorro_vista.constants import REPORTE_AHORRO_VISTA_SP


class SqlReporteAhorroVistaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_por_rango(self, fecha_desde: date, fecha_hasta: date) -> list[dict[str, Any]]:
        result = self.db.execute(
            text(
                f"""
                SET NOCOUNT ON;
                EXEC {REPORTE_AHORRO_VISTA_SP}
                    @FechaInicio = :fecha_desde,
                    @FechaFin = :fecha_hasta;
                """
            ),
            {"fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta},
        )
        if not result.returns_rows:
            raise RuntimeError("El SP de ahorros a la vista no devolvió columnas.")
        return [dict(row) for row in result.mappings().all()]

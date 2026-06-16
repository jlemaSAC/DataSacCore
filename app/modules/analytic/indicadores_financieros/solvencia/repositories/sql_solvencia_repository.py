from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable

from fastapi import HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, sessionmaker

from app.models.colocacion.prestamo_calificacion_provisiones_model import (
    PrestamoCalificacionProviciones,
)
from app.models.colocacion.prestamo_model import Prestamo
from app.models.general.agencia_model import Agencia


class SqlIndicadoresFinancierosRepository:
    def __init__(
        self,
        db: Session,
        secondary_session_factory: sessionmaker[Session],
    ) -> None:
        self.db = db
        self.secondary_session_factory = secondary_session_factory

    def get_nombre_agencia(self, id_agencia: int) -> str | None:
        if id_agencia == 1:
            return None
        nombre = self.db.query(Agencia.nombre).filter(Agencia.id == id_agencia).scalar()
        if not nombre:
            raise HTTPException(
                status_code=422,
                detail=f"No existe la agencia con id {id_agencia}.",
            )
        return str(nombre).strip()

    def get_ids_prestamos_activos(self, id_agencia: int) -> list[int]:
        ids_query = self.db.query(Prestamo.id).filter(Prestamo.codigo_estado != "C")
        if id_agencia != 1:
            ids_query = ids_query.filter(Prestamo.id_agencia == id_agencia)
        return [int(row[0]) for row in ids_query.all() if row[0] is not None]

    def sum_provision_requerida_viva(
        self,
        *,
        ids_prestamos: list[int],
        fecha_consulta: datetime,
    ) -> float:
        if not ids_prestamos:
            return 0.0

        provision_requerida = 0.0
        secondary_db = self.secondary_session_factory()
        try:
            for chunk in chunked(ids_prestamos):
                sub = (
                    secondary_db.query(
                        PrestamoCalificacionProviciones.id_prestamo.label("id_prestamo"),
                        PrestamoCalificacionProviciones.provision_automatica.label(
                            "provision_requerida"
                        ),
                        func.row_number()
                        .over(
                            partition_by=PrestamoCalificacionProviciones.id_prestamo,
                            order_by=(
                                desc(PrestamoCalificacionProviciones.fecha_calificacion),
                                desc(PrestamoCalificacionProviciones.fecha_proceso),
                                desc(PrestamoCalificacionProviciones.id),
                            ),
                        )
                        .label("rn"),
                    )
                    .filter(
                        PrestamoCalificacionProviciones.id_prestamo.in_(chunk),
                        PrestamoCalificacionProviciones.fecha_calificacion <= fecha_consulta,
                    )
                    .subquery()
                )
                rows = (
                    secondary_db.query(sub.c.provision_requerida)
                    .filter(sub.c.rn == 1)
                    .all()
                )
                for row in rows:
                    provision_requerida += to_float(row.provision_requerida)
        finally:
            secondary_db.close()

        return provision_requerida


def chunked(valores: list[int], size: int = 2000) -> Iterable[list[int]]:
    for idx in range(0, len(valores), size):
        yield valores[idx : idx + size]


def to_float(valor: Any) -> float:
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, Decimal):
        try:
            return float(valor)
        except Exception:
            return 0.0
    if hasattr(valor, "to_decimal"):
        try:
            return float(valor.to_decimal())
        except Exception:
            return 0.0
    if isinstance(valor, str):
        texto = valor.strip().replace("$", "").replace("%", "")
        if "," in texto and "." not in texto:
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
        try:
            return float(texto)
        except Exception:
            return 0.0
    return 0.0

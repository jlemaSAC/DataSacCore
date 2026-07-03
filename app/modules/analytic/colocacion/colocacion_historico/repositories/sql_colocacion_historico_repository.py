from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.colocacion.estado_prestamo_model import EstadoPrestamo
from app.models.colocacion.prestamo_cliente_model import PrestamoCliente
from app.models.colocacion.prestamo_model import Prestamo
from app.models.general.agencia_model import Agencia


class SqlColocacionHistoricoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_saldos_adjudicados_por_agencia(
        self,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> dict[str, float]:
        statement = (
            select(
                Agencia.nombre,
                func.sum(Prestamo.deuda_inicial).label("saldo_inicial"),
            )
            .select_from(Prestamo)
            .join(PrestamoCliente, PrestamoCliente.id_prestamo == Prestamo.id)
            .join(EstadoPrestamo, EstadoPrestamo.codigo == Prestamo.codigo_estado)
            .join(Agencia, Agencia.id == Prestamo.id_agencia)
            .where(PrestamoCliente.activo == True)
            .where(PrestamoCliente.es_principal == True)
            .where(EstadoPrestamo.nombre != "CANCELADO")
            .where(Prestamo.fecha_adjudicacion >= fecha_inicio)
            .where(Prestamo.fecha_adjudicacion <= fecha_fin)
            .group_by(Agencia.nombre)
        )

        saldos: dict[str, float] = {}
        for nombre, saldo in self.db.execute(statement):
            agencia = str(nombre or "SIN DATOS").strip().upper() or "SIN DATOS"
            saldos[agencia] = float(saldo or 0.0)
        return saldos

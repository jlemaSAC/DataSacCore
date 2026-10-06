from __future__ import annotations

from datetime import date, timedelta
from typing import NamedTuple

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.colocacion.prestamo_model import Prestamo
from app.models.general.agencia_model import Agencia
from app.models.nomina.empleado_model import Empleado
from app.models.nomina.empleado_usuario_model import EmpleadoUsuario
from app.models.seguridad.usuario_model import Usuario


class ColocacionAsesorDia(NamedTuple):
    codigo_usuario: str
    asesor: str
    operaciones_hoy: int
    monto_colocado_hoy: float
    operaciones_ayer: int
    monto_colocado_ayer: float


class ColocacionDiariaData(NamedTuple):
    id_agencia: int
    agencia: str
    asesores: list[ColocacionAsesorDia]


class SqlColocacionDiariaAsesoresRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_colocaciones(
        self,
        *,
        id_agencia: int,
        fecha: date,
    ) -> ColocacionDiariaData | None:
        nombre_agencia = (
            self.db.query(Agencia.nombre)
            .filter(Agencia.id == id_agencia)
            .scalar()
        )
        if not nombre_agencia:
            return None

        asesores = (
            self.db.query(
                Usuario.usuario.label("codigo_usuario"),
                Usuario.nombre.label("asesor"),
            )
            .select_from(Usuario)
            .join(EmpleadoUsuario, EmpleadoUsuario.codigo_usuario == Usuario.usuario)
            .join(Empleado, Empleado.id == EmpleadoUsuario.id_empleado)
            .filter(Usuario.id_agencia == id_agencia)
            .filter(Usuario.activo, Usuario.puede_ingresar_sistema)
            .filter(Empleado.codigo_estado_empleado == "A")
            .distinct()
            .subquery()
        )
        fecha_ayer = fecha - timedelta(days=1)
        operaciones_hoy = func.sum(
            case((Prestamo.fecha_adjudicacion >= fecha, 1), else_=0)
        )
        monto_hoy = func.sum(
            case((Prestamo.fecha_adjudicacion >= fecha, Prestamo.deuda_inicial), else_=0)
        )
        operaciones_ayer = func.sum(
            case((Prestamo.fecha_adjudicacion < fecha, 1), else_=0)
        )
        monto_ayer = func.sum(
            case((Prestamo.fecha_adjudicacion < fecha, Prestamo.deuda_inicial), else_=0)
        )
        filas = (
            self.db.query(
                asesores.c.codigo_usuario,
                asesores.c.asesor,
                func.coalesce(operaciones_hoy, 0).label("operaciones_hoy"),
                func.coalesce(monto_hoy, 0).label("monto_colocado_hoy"),
                func.coalesce(operaciones_ayer, 0).label("operaciones_ayer"),
                func.coalesce(monto_ayer, 0).label("monto_colocado_ayer"),
            )
            .join(Prestamo, Prestamo.codigo_usuario == asesores.c.codigo_usuario)
            .filter(Prestamo.id_agencia == id_agencia)
            .filter(
                Prestamo.fecha_adjudicacion >= fecha_ayer,
                Prestamo.fecha_adjudicacion < fecha + timedelta(days=1),
            )
            .group_by(asesores.c.codigo_usuario, asesores.c.asesor)
            .order_by(monto_hoy.desc(), asesores.c.asesor.asc())
            .all()
        )
        return ColocacionDiariaData(
            id_agencia=int(id_agencia),
            agencia=str(nombre_agencia).strip(),
            asesores=[
                ColocacionAsesorDia(
                    codigo_usuario=str(fila.codigo_usuario),
                    asesor=str(fila.asesor),
                    operaciones_hoy=int(fila.operaciones_hoy or 0),
                    monto_colocado_hoy=float(fila.monto_colocado_hoy or 0),
                    operaciones_ayer=int(fila.operaciones_ayer or 0),
                    monto_colocado_ayer=float(fila.monto_colocado_ayer or 0),
                )
                for fila in filas
            ],
        )

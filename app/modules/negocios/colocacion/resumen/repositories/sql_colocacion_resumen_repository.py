from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.models.colocacion.prestamo_model import Prestamo
from app.models.colocacion.prestamo_solicitud_model import PrestamoSolicitud
from app.models.credito.calificacion_contable_model import CalificacionContable
from app.models.credito.solicitud_prestamo_tipoemision_model import SolicitudPrestamoTipoEmision
from app.models.credito.subcalificacion_contable_model import SubcalificacionContable
from app.models.credito.tipo_emision_model import TipoEmision
from app.models.credito.tipo_prestamo_model import TipoPrestamo
from app.models.general.agencia_model import Agencia


DimensionResumen = Literal["tipo_prestamo", "producto", "segmento", "condicion"]


@dataclass(frozen=True)
class PeriodosComparacionColocacion:
    actual_inicio: date
    actual_fin: date
    anterior_inicio: date
    anterior_fin: date
    mes_a_fecha_inicio: date
    mes_a_fecha_fin: date
    mes_anterior_inicio: date
    mes_anterior_fin: date


@dataclass(frozen=True)
class TotalesColocacion:
    id_agencia: int
    agencia: str
    dimension: str | None
    monto_colocado: float
    monto_colocado_periodo_anterior: float
    monto_mes_a_fecha: float
    monto_mes_anterior_mismo_dia: float


class SqlColocacionResumenRepository:
    """Consulta las colocaciones adjudicadas y las agrega para el dashboard."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_por_agencia(
        self,
        agencia_ids: list[int],
        periodos: PeriodosComparacionColocacion,
    ) -> list[TotalesColocacion]:
        return self._obtener_totales(agencia_ids, periodos, dimension=None)

    def obtener_por_dimension(
        self,
        agencia_ids: list[int],
        periodos: PeriodosComparacionColocacion,
        dimension: DimensionResumen,
    ) -> list[TotalesColocacion]:
        return self._obtener_totales(agencia_ids, periodos, dimension=dimension)

    def _obtener_totales(
        self,
        agencia_ids: list[int],
        periodos: PeriodosComparacionColocacion,
        dimension: DimensionResumen | None,
    ) -> list[TotalesColocacion]:
        expresiones_dimension = {
            "tipo_prestamo": TipoPrestamo.nombre,
            "producto": CalificacionContable.nombre,
            "segmento": SubcalificacionContable.nombre,
            "condicion": TipoEmision.nombre,
        }
        expresion_dimension = expresiones_dimension.get(dimension) if dimension else None
        campos_grupo = [Agencia.id, Agencia.nombre]
        columnas = [
            Agencia.id.label("id_agencia"),
            func.coalesce(Agencia.nombre, "SIN DATOS").label("agencia"),
        ]
        if expresion_dimension is not None:
            dimension_normalizada = func.coalesce(expresion_dimension, "SIN DATOS")
            # SQL Server no reconoce como equivalente un COALESCE con parámetros
            # distintos en SELECT y GROUP BY. Agrupamos por la columna original y
            # normalizamos solamente la etiqueta que se expone en la respuesta.
            campos_grupo.append(expresion_dimension)
            columnas.append(dimension_normalizada.label("dimension"))

        periodo_actual = self._rango(periodos.actual_inicio, periodos.actual_fin)
        periodo_anterior = self._rango(periodos.anterior_inicio, periodos.anterior_fin)
        mes_a_fecha = self._rango(periodos.mes_a_fecha_inicio, periodos.mes_a_fecha_fin)
        mes_anterior = self._rango(periodos.mes_anterior_inicio, periodos.mes_anterior_fin)

        columnas.extend(
            [
                self._suma_condicional(periodo_actual).label("monto_colocado"),
                self._suma_condicional(periodo_anterior).label(
                    "monto_colocado_periodo_anterior"
                ),
                self._suma_condicional(mes_a_fecha).label("monto_mes_a_fecha"),
                self._suma_condicional(mes_anterior).label(
                    "monto_mes_anterior_mismo_dia"
                ),
            ]
        )
        statement = (
            select(*columnas)
            .select_from(Prestamo)
            .join(Agencia, Agencia.id == Prestamo.id_agencia)
            .outerjoin(
                SubcalificacionContable,
                SubcalificacionContable.codigo == Prestamo.codigo_subcalificacion_contable,
            )
            .outerjoin(
                CalificacionContable,
                CalificacionContable.codigo
                == SubcalificacionContable.codigo_calificacion_contable,
            )
            .outerjoin(PrestamoSolicitud, PrestamoSolicitud.id_prestamo == Prestamo.id)
            .outerjoin(
                SolicitudPrestamoTipoEmision,
                SolicitudPrestamoTipoEmision.id_solicitud == PrestamoSolicitud.id_solicitud,
            )
            .outerjoin(
                TipoEmision,
                TipoEmision.codigo == SolicitudPrestamoTipoEmision.codigo_tipo_emision,
            )
            .outerjoin(TipoPrestamo, TipoPrestamo.codigo == Prestamo.codigo_tipo_prestamo)
            .where(Prestamo.id_agencia.in_(agencia_ids))
            .where(or_(periodo_actual, periodo_anterior, mes_a_fecha, mes_anterior))
            .group_by(*campos_grupo)
            .order_by(Agencia.nombre.asc())
        )
        if expresion_dimension is not None:
            statement = statement.order_by(expresion_dimension.asc())

        resultado: list[TotalesColocacion] = []
        for row in self.db.execute(statement).mappings():
            resultado.append(
                TotalesColocacion(
                    id_agencia=int(row["id_agencia"]),
                    agencia=str(row["agencia"]),
                    dimension=str(row["dimension"]) if dimension else None,
                    monto_colocado=float(row["monto_colocado"] or 0),
                    monto_colocado_periodo_anterior=float(
                        row["monto_colocado_periodo_anterior"] or 0
                    ),
                    monto_mes_a_fecha=float(row["monto_mes_a_fecha"] or 0),
                    monto_mes_anterior_mismo_dia=float(
                        row["monto_mes_anterior_mismo_dia"] or 0
                    ),
                )
            )
        return resultado

    @staticmethod
    def _rango(fecha_inicio: date, fecha_fin: date):
        return and_(
            Prestamo.fecha_adjudicacion >= fecha_inicio,
            Prestamo.fecha_adjudicacion < fecha_fin + timedelta(days=1),
        )

    @staticmethod
    def _suma_condicional(condicion):
        return func.coalesce(
            func.sum(case((condicion, Prestamo.deuda_inicial), else_=0)),
            0,
        )

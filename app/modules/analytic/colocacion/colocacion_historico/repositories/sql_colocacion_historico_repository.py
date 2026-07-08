from datetime import date, datetime

from sqlalchemy import case, exists, func, select
from sqlalchemy.orm import Session

from app.models.clientes.cliente_model import Cliente
from app.models.colocacion.estado_prestamo_model import EstadoPrestamo
from app.models.colocacion.prestamo_cliente_model import PrestamoCliente
from app.models.colocacion.prestamo_garantiahipotecaria_model import PrestamoGarantiaHipotecaria
from app.models.colocacion.prestamo_garantiainversion_model import PrestamoGarantiaInversion
from app.models.colocacion.prestamo_garantiapersonal_model import PrestamoGarantiaPersonal
from app.models.colocacion.prestamo_garantiaprendaria_model import PrestamoGarantiaPrendaria
from app.models.colocacion.prestamo_model import Prestamo
from app.models.colocacion.prestamo_solicitud_model import PrestamoSolicitud
from app.models.credito.calificacion_contable_model import CalificacionContable
from app.models.credito.solicitud_prestamo_tipoemision_model import SolicitudPrestamoTipoEmision
from app.models.credito.subcalificacion_contable_model import SubcalificacionContable
from app.models.credito.tipo_emision_model import TipoEmision
from app.models.credito.tipo_prestamo_model import TipoPrestamo
from app.models.general.agencia_model import Agencia
from app.models.general.views.division_politica_consolidado import DivisionPoliticaConsolidado
from app.models.seguridad.usuario_model import Usuario
from app.models.sujeto.educacion_model import Educacion
from app.models.sujeto.persona_model import Persona
from app.models.sujeto.persona_natural_model import PersonaNatural
from app.modules.analytic.colocacion.colocacion_historico.domain import (
    ColocacionAgrupada,
    DimensionesColocacion,
)


def _normalizar(valor: object) -> str:
    return str(valor or "SIN DATOS").strip().upper() or "SIN DATOS"


def _calcular_edad(fecha_nacimiento: datetime | date | None, fecha_referencia: date) -> str:
    if fecha_nacimiento is None:
        return "SIN DATOS"
    nacimiento = fecha_nacimiento.date() if isinstance(fecha_nacimiento, datetime) else fecha_nacimiento
    edad = fecha_referencia.year - nacimiento.year - (
        (fecha_referencia.month, fecha_referencia.day) < (nacimiento.month, nacimiento.day)
    )
    if edad < 0:
        return "SIN DATOS"
    for limite in range(20, 101, 10):
        if edad <= limite:
            return f"HASTA {limite}"
    return "MAS DE 100"


class SqlColocacionHistoricoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_colocaciones_agrupadas(
        self,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> list[ColocacionAgrupada]:
        garantia = case(
            (
                exists(
                    select(1).where(
                        PrestamoGarantiaPersonal.id_prestamo == Prestamo.id,
                        PrestamoGarantiaPersonal.activo == 1,
                    )
                ),
                "PERSONAL",
            ),
            (
                exists(
                    select(1).where(
                        PrestamoGarantiaHipotecaria.id_prestamo == Prestamo.id,
                        PrestamoGarantiaHipotecaria.activo == 1,
                    )
                ),
                "HIPOTECARIA",
            ),
            (
                exists(
                    select(1).where(
                        PrestamoGarantiaInversion.id_prestamo == Prestamo.id,
                        PrestamoGarantiaInversion.activo == 1,
                    )
                ),
                "LIQUIDA",
            ),
            (
                exists(
                    select(1).where(
                        PrestamoGarantiaPrendaria.id_prestamo == Prestamo.id,
                        PrestamoGarantiaPrendaria.activo == 1,
                    )
                ),
                "PRENDARIA",
            ),
            else_="SIN GARANTIA",
        )
        base = (
            select(
                Prestamo.id.label("id_prestamo"),
                Prestamo.deuda_inicial.label("deuda_inicial"),
                Agencia.nombre.label("agencia"),
                TipoEmision.nombre.label("condicion"),
                TipoPrestamo.nombre.label("tipo_prestamo"),
                CalificacionContable.nombre.label("producto"),
                SubcalificacionContable.nombre.label("segmento"),
                func.coalesce(Usuario.nombre, Prestamo.codigo_usuario).label("asesor"),
                DivisionPoliticaConsolidado.provincia.label("provincia"),
                DivisionPoliticaConsolidado.canton.label("canton"),
                DivisionPoliticaConsolidado.parroquia.label("parroquia"),
                Educacion.nombre.label("educacion"),
                PersonaNatural.fecha_nacimiento.label("fecha_nacimiento"),
                garantia.label("garantia"),
            )
            .select_from(Prestamo)
            .join(PrestamoCliente, PrestamoCliente.id_prestamo == Prestamo.id)
            .join(EstadoPrestamo, EstadoPrestamo.codigo == Prestamo.codigo_estado)
            .join(Agencia, Agencia.id == Prestamo.id_agencia)
            .join(Cliente, Cliente.id == PrestamoCliente.id_cliente)
            .join(Persona, Persona.id == Cliente.id_persona)
            .outerjoin(PersonaNatural, PersonaNatural.id_persona == Persona.id)
            .outerjoin(Educacion, Educacion.codigo == PersonaNatural.codigo_educacion)
            .outerjoin(
                DivisionPoliticaConsolidado,
                DivisionPoliticaConsolidado.id_division_nivel_bajo == Persona.id_residencia,
            )
            .outerjoin(Usuario, Usuario.usuario == Prestamo.codigo_usuario)
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
            .where(PrestamoCliente.activo == 1)
            .where(PrestamoCliente.es_principal == 1)
            .where(EstadoPrestamo.nombre != "CANCELADO")
            .where(Prestamo.fecha_adjudicacion >= fecha_inicio)
            .where(Prestamo.fecha_adjudicacion <= fecha_fin)
            .distinct()
            .subquery()
        )
        columnas_grupo = (
            base.c.agencia,
            base.c.condicion,
            base.c.tipo_prestamo,
            base.c.producto,
            base.c.segmento,
            base.c.asesor,
            base.c.provincia,
            base.c.canton,
            base.c.parroquia,
            base.c.educacion,
            base.c.fecha_nacimiento,
            base.c.garantia,
        )
        statement = (
            select(
                *columnas_grupo,
                func.count(func.distinct(base.c.id_prestamo)).label("operaciones"),
                func.sum(base.c.deuda_inicial).label("saldo_inicial"),
            )
            .group_by(*columnas_grupo)
        )

        resultado: dict[DimensionesColocacion, ColocacionAgrupada] = {}
        for row in self.db.execute(statement):
            dimensiones = DimensionesColocacion(
                periodo=fecha_inicio.strftime("%Y-%m"),
                anio=fecha_inicio.year,
                mes=fecha_inicio.month,
                agencia=_normalizar(row[0]),
                condicion=_normalizar(row[1]),
                tipo_prestamo=_normalizar(row[2]),
                producto=_normalizar(row[3]),
                segmento=_normalizar(row[4]),
                asesor=_normalizar(row[5]),
                provincia=_normalizar(row[6]),
                canton=_normalizar(row[7]),
                parroquia=_normalizar(row[8]),
                educacion=_normalizar(row[9]),
                edad=_calcular_edad(row[10], fecha_fin.date()),
                garantia=_normalizar(row[11]),
            )
            actual = resultado.setdefault(
                dimensiones,
                ColocacionAgrupada(dimensiones=dimensiones, operaciones=0, saldo_inicial=0.0),
            )
            actual.operaciones += int(row[12] or 0)
            actual.saldo_inicial += float(row[13] or 0.0)
        return list(resultado.values())

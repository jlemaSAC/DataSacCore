from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base


class Empleado(Base):
    __tablename__ = "EMPLEADO"
    __table_args__ = {"schema": "NOMINA"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_persona_natural = Column('IDPERSONANATURAL', Integer, ForeignKey('SUJETO.PERSONA_NATURAL.IDPERSONA'), nullable=False)
    id_agencia_departamento = Column('IDAGENCIADEPARTAMENTO', Integer, ForeignKey('GENERAL.AGENCIA_DEPARTAMENTO.ID'), nullable=False)
    id_cargo = Column('IDCARGO', Integer, ForeignKey('NOMINA.CARGO.ID'), nullable=False)
    codigo_tipo_sangre = Column('CODIGOTIPOSANGRE', NVARCHAR(50), ForeignKey('NOMINA.TIPO_SANGRE.CODIGO'), nullable=False)
    codigo_tipo_licencia = Column('CODIGOTIPOLICENCIA', NVARCHAR(50), ForeignKey('NOMINA.TIPO_LICENCIA.CODIGO'), nullable=False)
    codigo_tipo_etnia = Column('CODIGOTIPOETNIA', NVARCHAR(50), ForeignKey('NOMINA.TIPO_ETNIA.CODIGO'), nullable=False)
    codigo_usuario_ingreso = Column('CODIGOUSUARIOINGRESO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)
    codigo_estado_empleado = Column('CODIGOESTADOEMPLEADO', NVARCHAR(10), ForeignKey('NOMINA.ESTADO_EMPLEADO.CODIGO'), nullable=False)
    id_empleado_jefe_inmediato = Column('IDEMPLEADO_JEFEINMEDIATO', Integer, nullable=False)
    recibe_fondos_reserva = Column('RECIBEFONDOSRESERVA', Boolean, nullable=False)
    codigo_condicion_discapacidad = Column('CODIGOCONDICIONDISCAPACIDAD', NVARCHAR(50), ForeignKey('NOMINA.CONDICION_DISCAPACIDAD.CODIGO'), nullable=False)
    permite_consulta = Column('PERMITECONSULTA', Boolean, nullable=False)
    recibe_quincena = Column('RECIBEQUINCENA', Boolean, nullable=False)
    id_funcionario = Column('IDFUNCIONARIO', Integer, ForeignKey('NOMINA.FUNCIONARIO.ID'), nullable=True, unique=True)
    permite_consulta_buro = Column('PERMITECONSULTABURO', Boolean, nullable=False)
    enviado_sarf = Column('ENVIADOSARF', Boolean, nullable=False)

    # Relaciones con backref

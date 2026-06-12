from sqlalchemy import Column, DateTime, DECIMAL, Integer

from sqlalchemy import Column, Integer, Boolean, DateTime, UniqueConstraint
from sqlalchemy.dialects.mssql import NVARCHAR, DECIMAL
from app.db.base import BaseSecundaria


class PrestamoCalificacionProviciones(BaseSecundaria):
    __tablename__ = "PRESTAMO_CALIFICACION"
    __table_args__ = (
        UniqueConstraint(
            "IDPRESTAMO",
            "FECHACALIFICACION",
            name="IX_PRESTAMO_CALIFICACION",
        ),
        {"schema": "COLOCACION"},   
    )

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_prestamo = Column('IDPRESTAMO', Integer, nullable=False)
    fecha_calificacion = Column('FECHACALIFICACION', DateTime, nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)
    dia_mora = Column('DIA_MORA', Integer, nullable=False)
    saldo = Column('SALDO', DECIMAL(18, 2), nullable=False)
    id_calificacion_prestamo_informacion = Column('IDCALIFICACIONPRESTAMOINFORMACION', Integer, nullable=False)
    calificacion = Column('CALIFICACION', NVARCHAR(5), nullable=False)
    porcentaje_fijo = Column('PORCENTAJE_FIJO', DECIMAL(18, 2), nullable=False)
    provision_automatica = Column('PROVISIONAUTOMATICA', DECIMAL(18, 2), nullable=False)
    provision_manual = Column('PROVISIONMANUAL', DECIMAL(18, 2), nullable=False)
    provision_constituida = Column('PROVISIONCONSTITUIDA', DECIMAL(18, 2), nullable=False)
    id_calificacion_prestamo_informacion_original = Column('IDCALIFICACIONPRESTAMOINFORMACIONORIGINAL', Integer, nullable=False)
    provision_original = Column('PROVISIONORIGINAL', DECIMAL(18, 2), nullable=False)
    codigo_usuario = Column('CODIGOUSUARIO', NVARCHAR(100), nullable=False)
    se_homologo = Column('SEHOMOLOGO', Boolean, nullable=False)
    codigo_estado_prestamo = Column('CODIGOESTADOPRESTAMO', NVARCHAR(10), nullable=True)


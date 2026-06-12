from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.mssql import NVARCHAR, DECIMAL
from sqlalchemy.orm import relationship

from app.db.base import Base


class PrestamoCalificacion(Base):
    __tablename__ = "PRESTAMO_CALIFICACION"
    __table_args__ = (
        UniqueConstraint("IDPRESTAMO","FECHACALIFICACION",name="IX_PRESTAMO_CALIFICACION",),
        Index("IX_PRESTAMO_CALIFICACION_FECHACALIFICACION","FECHACALIFICACION",
            mssql_include=[
                "IDPRESTAMO",
                "IDCALIFICACIONPRESTAMOINFORMACION",
                "CALIFICACION",
            ],
        ),
        {"schema": "COLOCACION"},
    )

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_prestamo = Column("IDPRESTAMO",Integer,ForeignKey("COLOCACION.PRESTAMO.ID"),nullable=False,)
    fecha_calificacion = Column("FECHACALIFICACION", DateTime, nullable=False)
    fecha_proceso = Column("FECHAPROCESO", DateTime, nullable=False)
    dia_mora = Column("DIA_MORA", Integer, nullable=False)
    saldo = Column("SALDO", DECIMAL(18, 2), nullable=False)
    id_calificacion_prestamo_informacion = Column("IDCALIFICACIONPRESTAMOINFORMACION",Integer,ForeignKey("COLOCACION.CALIFICACION_PRESTAMO_INFORMACION.ID"),nullable=False,)
    calificacion = Column("CALIFICACION", NVARCHAR(5), nullable=False)
    porcentaje_fijo = Column("PORCENTAJE_FIJO", DECIMAL(18, 2), nullable=False)
    provision_automatica = Column("PROVISIONAUTOMATICA", DECIMAL(18, 2), nullable=False)
    provision_manual = Column("PROVISIONMANUAL", DECIMAL(18, 2), nullable=False)
    provision_constituida = Column("PROVISIONCONSTITUIDA", DECIMAL(18, 2), nullable=False)
    id_calificacion_prestamo_informacion_original = Column("IDCALIFICACIONPRESTAMOINFORMACIONORIGINAL",Integer,ForeignKey("COLOCACION.CALIFICACION_PRESTAMO_INFORMACION.ID"),nullable=False,)
    provision_original = Column("PROVISIONORIGINAL", DECIMAL(18, 2), nullable=False)
    codigo_usuario = Column("CODIGOUSUARIO",NVARCHAR(100),ForeignKey("SEGURIDAD.USUARIO.USUARIO"),nullable=False)
    se_homologo = Column("SEHOMOLOGO", Boolean, nullable=False)
    # En la tabla no hay FK para este campo, lo dejamos como NVARCHAR simple
    codigo_estado_prestamo = Column(
        "CODIGOESTADOPRESTAMO",
        NVARCHAR(10),
        nullable=True,
    )
    # Relaciones (ajusta los back_populates según tengas definidos los otros modelos)
    prestamo = relationship("Prestamo", back_populates="prestamo_calificaciones")
    # calificacion_prestamo_informacion = relationship("CalificacionPrestamoInformacion",foreign_keys=[id_calificacion_prestamo_informacion],back_populates="prestamo_calificaciones",)
    # calificacion_prestamo_informacion_original = relationship("CalificacionPrestamoInformacion",foreign_keys=[id_calificacion_prestamo_informacion_original],back_populates="prestamo_calificaciones_originales",)
    usuario = relationship("Usuario",back_populates="prestamo_calificaciones")
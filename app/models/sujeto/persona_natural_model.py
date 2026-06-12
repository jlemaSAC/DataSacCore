
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class PersonaNatural(Base):
    __tablename__ = "PERSONA_NATURAL"
    __table_args__ = {"schema": "SUJETO"}

    id_persona = Column("IDPERSONA", Integer, ForeignKey("SUJETO.PERSONA.ID"), primary_key=True)
    codigo_estado_civil = Column("CODIGOESTADOCIVIL", String(10), nullable=False)
    primer_nombre = Column("PRIMERNOMBRE", String(150), nullable=True)
    segundo_nombre = Column("SEGUNDONOMBRE", String(150), nullable=True)
    apellido_paterno = Column("APELLIDOPATERNO", String(150), nullable=True)
    apellido_materno = Column("APELLIDOMATERNO", String(150), nullable=True)
    es_masculino = Column("ESMASCULINO", Boolean, nullable=False)
    fecha_nacimiento = Column("FECHANACIMIENTO", DateTime, nullable=False)
    codigo_educacion = Column("CODIGOEDUCACION", String(10), nullable=False)
    codigo_vivienda = Column("CODIGOVIVIENDA", String(10), nullable=False)
    codigo_profesion = Column("CODIGOPROFESION", String(10), nullable=False)
    cobra_bono_desarrollo_humano = Column("COBRABONODESARROLLOHUMANO", Boolean, nullable=False)
    codigo_sector_vivienda = Column("CODIGOSECTORVIVIENDA", String(50), nullable=True)
    es_separacion_de_bienes = Column("ESSEPARACIONDEBIENES", Boolean, nullable=False)
    ciudad_nacimiento = Column("CIUDADNACIMIENTO", String(200), nullable=True)
    tiene_huella = Column("TIENEHUELLA", Boolean, nullable=True)
    codigo_dactilar = Column("CODIGODACTILAR", String(100), nullable=True)
    id_lugar_nacimiento = Column("IDLUGARNACIMIENTO", Integer, ForeignKey("GENERAL.DIVISION_POLITICA.ID"), nullable=False)
    id_pais_nacimiento = Column("IDPAISNACIMIENTO", Integer, ForeignKey("GENERAL.PAIS.ID"), nullable=False)
    tiempo_residencia = Column("TIEMPORESIDENCIA", Integer, nullable=False)
    codigo_etnia = Column("CODIGOETNIA", String(3), ForeignKey("SUJETO.ETNIA.CODIGO"), nullable=True)
    es_grupo_prioritario = Column("ESGRUPOPRIORITARIO", Boolean, nullable=True, default=False)

    personas = relationship("Persona", back_populates="persona_natural")
    empleados = relationship("Empleado", back_populates="persona_natural")
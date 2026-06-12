from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoPrestamoEtapa(Base):
    __tablename__ = "TIPO_PRESTAMO_ETAPA"
    __table_args__ = {"schema": "CREDITO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_prestamo = Column(
        "CODIGOTIPOPRESTAMO",
        NVARCHAR(30),
        ForeignKey("CREDITO.TIPO_PRESTAMO.CODIGO"),
        nullable=False,
    )
    id_etapa = Column("IDETAPA", Integer, ForeignKey("FLUJOTRABAJO.ETAPA.ID"), nullable=False)
    edita_solicitud = Column("EDITASOLICITUD", Boolean, nullable=False)
    permite_calificar = Column("PERMITECALIFICAR", Boolean, nullable=False)
    permite_anexo = Column("PERMITEANEXO", Boolean, nullable=False)
    imprime_pagare = Column("IMPRIMEPAGARE", Boolean, nullable=False)
    genera_prestamo = Column("GENERAPRESTAMO", Boolean, nullable=False)
    requiere_emision = Column("REQUIEREEMISION", Boolean, nullable=False)
    es_comite = Column("ESCOMITE", Boolean, nullable=False)
    es_agricola = Column("ESAGRICOLA", Boolean, nullable=True)
    vista_multiple = Column("VISTAMULTIPLE", Boolean, nullable=True)
    activa = Column("ACTIVA", Boolean, nullable=False)

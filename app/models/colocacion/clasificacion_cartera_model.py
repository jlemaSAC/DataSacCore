from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from app.db.base import Base


class ClasificacionCartera(Base):
    __tablename__ = "CLASIFICACION_CARTERA"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_calificacion_contable = Column(
        "CODIGOCALIFICACIONCONTABLE",
        String(30),
        ForeignKey("CREDITO.CALIFICACION_CONTABLE.CODIGO"),
        nullable=False,
    )
    dias_inicio = Column("DIASINICIO", Integer, nullable=False)
    dias_fin = Column("DIASFIN", Integer, nullable=False)
    codigo_cuenta_contable = Column("CODIGOCUENTACONTABLE", String(50), nullable=False)
    codigo_tipo_vencimiento = Column(
        "CODIGOTIPOVENCIMIENTO",
        String(10),
        ForeignKey("COLOCACION.TIPO_VENCIMIENTO.CODIGO"),
        nullable=False,
    )
    activo = Column("ACTIVO", Boolean, nullable=False)

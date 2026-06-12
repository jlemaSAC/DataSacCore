from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer
from app.db.base import Base


class CalendarioSistema(Base):
    __tablename__ = "CALENDARIO_SISTEMA"
    __table_args__ = {"schema": "GENERAL"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column("IDEMPRESA", Integer, ForeignKey("GENERAL.EMPRESA.ID"), nullable=False)
    fecha_sistema = Column("FECHASISTEMA", DateTime, nullable=False)
    es_feriado = Column("ESFERIADO", Boolean, nullable=False)
    dia_habil = Column("DIAHABIL", Boolean, nullable=False)
    se_cerro = Column("SECERRO", Boolean, nullable=False)
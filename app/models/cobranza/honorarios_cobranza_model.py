from sqlalchemy import Column, Integer, Boolean, DECIMAL, ForeignKey
from app.db.base import Base


class HonorariosCobranza(Base):
    __tablename__ = "HONORARIOS_COBRANZA"
    __table_args__ = {"schema": "COBRANZA"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column('IDEMPRESA', Integer, ForeignKey('GENERAL.EMPRESA.ID'), nullable=False)
    valor_cuota_inicio = Column('VALORCUOTAINICIO', DECIMAL(18, 2), nullable=False)
    valor_cuota_fin = Column('VALORCUOTAFIN', DECIMAL(18, 2), nullable=False)
    es_porcentaje = Column('ESPORCENTAJE', Boolean, nullable=False)

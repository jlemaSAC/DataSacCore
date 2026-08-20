from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary
from sqlalchemy.dialects.mssql import DECIMAL, NVARCHAR

from app.db.base import Base


class ItemSaldoTasa(Base):
    __tablename__ = "ITEMSALDO_TASA"
    __table_args__ = {"schema": "AHORROS"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_item = Column("IDITEM", Integer, ForeignKey("AHORROS.ITEMSALDO.ID"), nullable=False)
    id_item_acumula = Column("IDITEMACUMULA", Integer, ForeignKey("AHORROS.ITEMSALDO.ID"), nullable=False)
    saldo_inicial = Column("SALDOINICIAL", DECIMAL(18, 2), nullable=False)
    saldo_final = Column("SALDOFINAL", DECIMAL(18, 2), nullable=False)
    tasa = Column("TASA", DECIMAL(18, 2), nullable=False)
    codigo_usuario = Column("CODIGOUSUARIO", NVARCHAR(100, collation="Modern_Spanish_CI_AS"), ForeignKey("SEGURIDAD.USUARIO.USUARIO"), nullable=False)
    fecha_registro = Column("FECHAREGISTRO", DateTime, nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
    version = Column("VERSION", LargeBinary, nullable=False)
    fecha_inicio = Column("FECHAINICIO", DateTime, nullable=False)
    fecha_fin = Column("FECHAFIN", DateTime, nullable=False)

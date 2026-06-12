from sqlalchemy import Column, Integer, DateTime, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR, VARCHAR
from app.db.base import Base


class MovimientoAfectacionDetalleVista(Base):
    __tablename__ = "MOVIMIENTO_AFECTACION_DETALLE_VISTA"
    __table_args__ = {"schema": "FINANCIERO"}  # ajusta si tu schema difiere

    id = Column('ID', Integer, primary_key=True, nullable=False)

    documento = Column('DOCUMENTO', NVARCHAR(100), nullable=False)
    es_movimiento_transaccion = Column('ESMOVIMIENTOTRANSACCION', Integer, nullable=False)

    hora = Column('HORA', DateTime, nullable=False)
    fecha = Column('FECHA', DateTime, nullable=False)

    detalle = Column('DETALLE', NVARCHAR(4000), nullable=True)
    debito = Column('DEBITO', Numeric(18, 6), nullable=True)
    credito = Column('CREDITO', Numeric(18, 6), nullable=True)

    producto = Column('PRODUCTO', VARCHAR(15), nullable=True)      # varchar (no nvarchar)
    codigo = Column('CODIGO', NVARCHAR(514), nullable=True)

    numero = Column('NUMERO', Integer, nullable=False)
    identificacion = Column('IDENTIFICACION', NVARCHAR(50), nullable=False)
    cliente = Column('CLIENTE', NVARCHAR(150), nullable=False)
    usuario = Column('USUARIO', NVARCHAR(150), nullable=False)

    codigo_cuentacontable = Column('CODIGOCUENTACONTABLE', NVARCHAR(50), nullable=True)
from sqlalchemy import Column, DateTime, Integer, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR, VARCHAR
from app.db.base import Base


class MovimientoTransaccionDetalleVista(Base):
    __tablename__ = "MOVIMIENTO_TRANSACCION_DETALLE_VISTA"
    __table_args__ = {"schema": "FINANCIERO"}  

    id = Column("ID", Integer, primary_key=True, nullable=False)

    documento = Column("DOCUMENTO", NVARCHAR(100), nullable=False)
    es_movimiento_transaccion = Column("ESMOVIMIENTOTRANSACCION", Integer, nullable=False)
    es_opcional = Column("ESOPCIONAL", Integer, nullable=False)

    hora = Column("HORA", DateTime, nullable=False)
    fecha_sistema = Column("FECHASISTEMA", DateTime, nullable=False)

    detalle = Column("DETALLE", NVARCHAR(655), nullable=True)
    debito = Column("DEBITO", Numeric(38, 2), nullable=True)
    credito = Column("CREDITO", Numeric(38, 2), nullable=True)

    producto = Column("PRODUCTO", VARCHAR(24), nullable=True)     # varchar, no nvarchar
    codigo = Column("CODIGO", NVARCHAR(521), nullable=True)
    numero = Column("NUMERO", Integer, nullable=False)

    identificacion = Column("IDENTIFICACION", NVARCHAR(100), nullable=False)
    cliente = Column("CLIENTE", NVARCHAR(200), nullable=False)
    usuario = Column("USUARIO", NVARCHAR(150), nullable=False)

    codigo_cuentacontable = Column("CODIGOCUENTACONTABLE", NVARCHAR(50), nullable=False)
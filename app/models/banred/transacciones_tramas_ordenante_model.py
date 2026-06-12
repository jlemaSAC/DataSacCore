from sqlalchemy import Boolean, Column, DateTime, Index, Integer, text
from sqlalchemy.dialects.mssql import VARCHAR

from app.db.base import Base


class TransaccionesTramasOrdenante(Base):
    __tablename__ = "TRANSACCIONESTRAMASORDENANTE"
    __table_args__ = {"schema": "BANRED"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_mensaje = Column('CODIGOMENSAJE', VARCHAR(15), nullable=True)
    identidad = Column('IDENTIDAD', VARCHAR(6), nullable=True)
    xml_data = Column('XMLDATA', VARCHAR(None), nullable=True)
    fecha_ingreso = Column('FECHAINGRESO', DateTime, nullable=True)
    other_id = Column('OTHERID', VARCHAR(6), nullable=True)
    id_mge = Column('IDMGE', VARCHAR(30), nullable=True)
    end_to_end = Column('ENDTOEND', VARCHAR(20), nullable=True)
    cuenta_beneficiario = Column('CUENTABENEFICIARIO', VARCHAR(20), nullable=True)
    identificacion_beneficiario = Column('IDENTIFICACIONBENEFICIARIO', VARCHAR(15), nullable=True)
    cuenta_debito = Column('CUENTADEBITO', VARCHAR(30), nullable=True)
    documento = Column('DOCUMENTO', VARCHAR(30), nullable=True)
    resultado = Column('RESULTADO', VARCHAR(4), nullable=True)
    error = Column('ERROR', VARCHAR(6), nullable=True)
    es_notificacion = Column('ESNOTIFICACION', Boolean, server_default=text('0'), nullable=True)
    fecha_xml = Column('FECHAXML', DateTime, nullable=True)
    xml_data_envio = Column('XMLDATAENVIO', VARCHAR(None), nullable=True)
    tipo_transaccion = Column('TIPOTRANSACCION', VARCHAR(6), nullable=True)

Index(
    "IX_TRAMASORDENANTE_DOC_FECHA",
    TransaccionesTramasOrdenante.documento,
    TransaccionesTramasOrdenante.fecha_ingreso,
    mssql_include=[
        "TIPOTRANSACCION",
        "RESULTADO",
        "CUENTABENEFICIARIO",
        "IDENTIDAD",
        "FECHAXML",
    ],
)
Index(
    "IX_TRAMASORDENANTE_FECHAXML",
    TransaccionesTramasOrdenante.fecha_xml,
)
Index(
    "IX_TRANSACCIONESTRAMASORDENANTE_DOCUMENTO",
    TransaccionesTramasOrdenante.documento,
)
Index(
    "IX_TRANSACCIONESTRAMASORDENANTE_FECHAINGRESO",
    TransaccionesTramasOrdenante.fecha_ingreso,
    TransaccionesTramasOrdenante.documento,
)

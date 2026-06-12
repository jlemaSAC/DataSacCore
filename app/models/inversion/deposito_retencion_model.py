from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class DepositoRetencion(Base):
    __tablename__ = "DEPOSITO_RETENCION"
    __table_args__ = {"schema": "INVERSION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_deposito = Column("IDDEPOSITO", Integer, ForeignKey("INVERSION.DEPOSITO.ID"), nullable=False)
    fecha_emision = Column("FECHAEMISION", DateTime, nullable=False)
    codigo_retencion_aplicada = Column("CODIGORETENCIONAPLICADA", NVARCHAR(10), nullable=False)
    monto = Column("MONTO", Numeric(18, 2), nullable=False)
    base_imponible = Column("BASEIMPONIBLE", Numeric(18, 2), nullable=False)
    porcentaje = Column("PORCENTAJE", Numeric(18, 2), nullable=False)
    valor_retenido = Column("VALORRETENIDO", Numeric(18, 2), nullable=False)
    establecimiento = Column("ESTABLECIMIENTO", NVARCHAR(6), nullable=False)
    punto_emision = Column("PUNTOEMISION", NVARCHAR(6), nullable=False)
    secuencia = Column("SECUENCIA", NVARCHAR(10), nullable=False)
    autorizacion = Column("AUTORIZACION", NVARCHAR(100), nullable=False)
    pago_local_exterior = Column("PAGOLOCALEXTERIOR", Boolean, nullable=False)
    pais_efectivo_pago = Column("PAISEFECTIVOPAGO", NVARCHAR(3), nullable=False)
    aplica_convenio_doble_tribut = Column("APLICACONVENIODOBLETRIBUT", NVARCHAR(2), nullable=False)
    pag_ext_suj_ret_nor_leg = Column("PAGEXTSUJRETNORLEG", NVARCHAR(2), nullable=False)
    pago_regimen_fiscal = Column("PAGOREGIMENFISCAL", NVARCHAR(2), nullable=False)
    esta_impreso = Column("ESTAIMPRESO", Boolean, nullable=False)
    esta_anulado = Column("ESTAANULADO", Boolean, nullable=False)
    clave_acceso = Column("CLAVEACCESO", NVARCHAR(50), nullable=False)

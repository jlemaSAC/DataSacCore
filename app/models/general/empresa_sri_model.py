from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, ForeignKey

from app.db.base import Base

class EmpresaSRI(Base):
    __tablename__ = "EMPRESA_SRI"
    __table_args__ = {"schema": "GENERAL"}

    idempresa = Column('IDEMPRESA', Integer, primary_key=True)
    ruc = Column('RUC', String(20), nullable=False)
    razonsocial = Column('RAZONSOCIAL', String(150), nullable=False)
    nombrecomercial = Column('NOMBRECOMERCIAL', String(150))
    direccion = Column('DIRECCION', String(250), nullable=False)
    telefono = Column('TELEFONO', String(20), nullable=False)
    email = Column('EMAIL', String(50), nullable=False)
    tipoidrepresentante = Column('TIPOIDREPRESENTANTE', Integer, ForeignKey('SUJETO.TIPO_IDENTIFICACION.ID'), nullable=False)
    idrepresentante = Column('IDREPRESENTANTE', Integer, nullable=False)
    idcontador = Column('IDCONTADOR', Integer, nullable=False)
    porcentajeiva = Column('PORCENTAJEIVA', DECIMAL(18, 2), nullable=False)
    porcentaleiva0 = Column('PORCENTALEIVA0', DECIMAL(18, 2), nullable=False)
    codigocausaliva = Column('CODIGOCAUSALIVA', String(50), ForeignKey('CONTABILIDAD.CAUSAL.CODIGO'), nullable=False)
    codigocausaliva0 = Column('CODIGOCAUSALIVA0', String(50), ForeignKey('CONTABILIDAD.CAUSAL.CODIGO'), nullable=False)
    escomprobante_electronico = Column('ESCOMPROBANTE_ELECTRONICO', Boolean, nullable=False)
    emite_enlinea = Column('EMITE_ENLINEA', Boolean, nullable=False)
    obligadocontabilidad = Column('OBLIGADOCONTABILIDAD', Boolean, nullable=False)
    contribuyenteespecial = Column('CONTRIBUYENTEESPECIAL', String(10), nullable=False)
    moneda = Column('MONEDA', String(10))
    urlservicio = Column('URLSERVICIO', String(500), nullable=False)
    urlimpresor = Column('URLIMPRESOR', String(100), nullable=False)
    urlconsulta = Column('URLCONSULTA', String(100), nullable=False)
    codigocausaliva14 = Column('CODIGOCAUSALIVA14', String(50), ForeignKey('CONTABILIDAD.CAUSAL.CODIGO'), nullable=False)
    codigocausalice = Column('CODIGOCAUSALICE', String(50), ForeignKey('CONTABILIDAD.CAUSAL.CODIGO'), nullable=False)
    porcentaleiva14 = Column('PORCENTALEIVA14', DECIMAL(18, 2), nullable=False)
    urlservicioapi = Column('URLSERVICIOAPI', String(500), nullable=False, default='https://localhost:7118/api/facturacionElectronica/comprobante_Electronico_Sri/procesaComprobanteFactura')
    urlservicioenvioapi = Column('URLSERVICIOENVIOAPI', String(500), nullable=False, default='http://192.168.1.9:9842/api/facturacionElectronica/comprobante_Electronico_Sri/enviaComprobantes')
    urlretencionapi = Column('URLRETENCIONAPI', String(500), nullable=False, default='http://192.168.1.9:9842/api/facturacionElectronica/comprobante_Electronico_Sri/procesaComprobanteRetencion')
    porcentajeiva5 = Column('PORCENTAJEIVA5', DECIMAL(18, 2))

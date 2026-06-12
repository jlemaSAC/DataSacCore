from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.mssql import NVARCHAR, DECIMAL
from app.db.base import Base


class SaldoContable(Base):
    __tablename__ = "SALDOCONTABLE"
    __table_args__ = (
        # UNIQUE (CODIGOCUENTA, FECHA, IDAGENCIA, IDMONEDA)
        UniqueConstraint(
            "CODIGOCUENTA", "FECHA", "IDAGENCIA", "IDMONEDA",
            name="IX_SALDOCONTABLE",
        ),
        {"schema": "CONTABILIDAD"},
    )

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_cuenta = Column('CODIGOCUENTA', NVARCHAR(50), ForeignKey('CONTABILIDAD.CUENTACONTABLE.CODIGO'), nullable=False)
    id_agencia = Column('IDAGENCIA', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False)
    id_moneda = Column('IDMONEDA', Integer, ForeignKey('GENERAL.MONEDA.ID'), nullable=False)
    fecha = Column('FECHA', DateTime, nullable=False)
    saldo_inicial = Column('SALDOINICIAL', DECIMAL(18, 2), nullable=False)
    total_debito = Column('TOTALDEBITO', DECIMAL(18, 2), nullable=False)
    total_credito = Column('TOTALCREDITO', DECIMAL(18, 2), nullable=False)
    cerrado = Column('CERRADO', Boolean, nullable=False)

# Índices no cluster en SQL Server con columnas incluidas
Index(
    "IX_SALDOCONTABLE_CODIGOCUENTA_IDAGENCIA_FECHA",
    SaldoContable.codigo_cuenta,
    SaldoContable.id_agencia,
    SaldoContable.fecha,
    mssql_include=["SALDOINICIAL", "TOTALDEBITO", "TOTALCREDITO"],
)

Index(
    "IX_SALDOCONTABLE_IDAGENCIA_FECHA",
    SaldoContable.id_agencia,
    SaldoContable.fecha,
    mssql_include=["CODIGOCUENTA", "IDMONEDA", "SALDOINICIAL", "TOTALDEBITO", "TOTALCREDITO"],
)

Index(
    "IX_SALDOCONTABLE_IDAGENCIA_FECHA_1",
    SaldoContable.id_agencia,
    SaldoContable.fecha,
    mssql_include=["ID", "CODIGOCUENTA", "IDMONEDA", "SALDOINICIAL", "TOTALDEBITO", "TOTALCREDITO", "CERRADO"],
)




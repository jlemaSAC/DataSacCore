from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import relationship

from app.db.base import Base


class PrestamoUsuarioControl(Base):
    __tablename__ = "PRESTAMO_USUARIO_CONTROL"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_prestamo = Column("IDPRESTAMO", Integer, nullable=False)
    codigo_usuario_control = Column(
        "CODIGOUSUARIOCONTROL",
        NVARCHAR(100, collation="Modern_Spanish_CI_AS"),
        ForeignKey("SEGURIDAD.USUARIO.USUARIO"),
        nullable=False,
    )
    nivel = Column("NIVEL", Integer, nullable=False)
    codigo_usuario_cobranza_apoyo = Column(
        "CODIGOUSUARIOCOBRANZAAPOYO",
        NVARCHAR(100, collation="Modern_Spanish_CI_AS"),
        nullable=False,
        default="",
    )

    usuario_control = relationship(
        "Usuario",
        foreign_keys=[codigo_usuario_control],
        back_populates="prestamos_usuario_control",
    )

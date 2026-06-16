from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Usuario(Base):
    __tablename__ = "USUARIO"
    __table_args__ = {"schema": "SEGURIDAD"}

    usuario: Mapped[str] = mapped_column("USUARIO",NVARCHAR(100),primary_key=True,nullable=False)
    nombre: Mapped[str] = mapped_column("NOMBRE",NVARCHAR(150),nullable=False)
    clave: Mapped[str] = mapped_column("CLAVE",NVARCHAR(None),nullable=False)
    id_agencia: Mapped[int] = mapped_column("IDAGENCIA",Integer,ForeignKey("GENERAL.AGENCIA.ID"),nullable=False)
    email: Mapped[str] = mapped_column("EMAIL",NVARCHAR(200),nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column("FECHACREACION",DateTime,nullable=False)
    fecha_cambio_clave: Mapped[datetime] = mapped_column("FECHACAMBIOCLAVE",DateTime,nullable=False)
    cambia_clave: Mapped[bool] = mapped_column("CAMBIACLAVE",Boolean,nullable=False)
    dias_cambio_clave: Mapped[int] = mapped_column("DIASCAMBIOCLAVE",Integer,nullable=False)
    tiene_bloqueo: Mapped[bool] = mapped_column("TIENEBLOQUEO",Boolean,nullable=False)
    puede_ingresar_sistema: Mapped[bool] = mapped_column("PUEDEINGRESARSISTEMA",Boolean,nullable=False)
    activo: Mapped[bool] = mapped_column("ACTIVO",Boolean,nullable=False)
    sesion_unica: Mapped[bool] = mapped_column("SESIONUNICA",Boolean,nullable=False,default=False)
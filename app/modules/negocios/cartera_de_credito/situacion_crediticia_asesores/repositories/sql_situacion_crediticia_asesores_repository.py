from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.general.agencia_model import Agencia
from app.models.nomina.cargo_model import Cargo
from app.models.nomina.empleado_model import Empleado
from app.models.nomina.empleado_usuario_model import EmpleadoUsuario
from app.models.seguridad.usuario_model import Usuario


class SqlSituacionCrediticiaAsesoresRepository:
    """Consultas auxiliares SQL; no ejecuta el procedimiento de cartera."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_nombre_agencia(self, id_agencia: int) -> str | None:
        nombre = (
            self.db.query(Agencia.nombre)
            .filter(Agencia.id == id_agencia)
            .scalar()
        )
        return str(nombre).strip() if nombre else None

    def obtener_gerentes_oficina(
        self,
        agencias: Iterable[str],
    ) -> list[dict[str, object]]:
        agencias_normalizadas = sorted(
            {
                str(agencia).strip()
                for agencia in agencias
                if agencia is not None and str(agencia).strip()
            }
        )
        if not agencias_normalizadas:
            return []

        rows = (
            self.db.query(
                Agencia.id.label("IdAgencia"),
                Agencia.nombre.label("Agencia"),
                Usuario.usuario.label("CodigoUsuarioGerente"),
                Usuario.nombre.label("GerenteOficina"),
                Cargo.nombre.label("Cargo"),
                Empleado.fecha_proceso.label("FechaProceso"),
            )
            .select_from(Agencia)
            .join(Usuario, Usuario.id_agencia == Agencia.id)
            .join(EmpleadoUsuario, EmpleadoUsuario.codigo_usuario == Usuario.usuario)
            .join(Empleado, Empleado.id == EmpleadoUsuario.id_empleado)
            .join(Cargo, Cargo.id == Empleado.id_cargo)
            .filter(
                Agencia.nombre.in_(agencias_normalizadas),
            Usuario.activo == True,
            Cargo.activo == True,
                func.upper(Cargo.nombre) == "JEFE DE AGENCIA",
            )
            .order_by(
                Agencia.nombre.asc(),
                Empleado.fecha_proceso.desc(),
                Usuario.nombre.asc(),
            )
            .all()
        )

        resultado: dict[str, dict[str, object]] = {}
        for row in rows:
            agencia = str(row.Agencia).strip() if row.Agencia else ""
            if agencia and agencia not in resultado:
                resultado[agencia] = {
                    "IdAgencia": int(row.IdAgencia),
                    "Agencia": agencia,
                    "CodigoUsuarioGerente": row.CodigoUsuarioGerente,
                    "GerenteOficina": row.GerenteOficina,
                    "Cargo": row.Cargo,
                }

        return [
            resultado.get(
                agencia,
                {
                    "IdAgencia": None,
                    "Agencia": agencia,
                    "CodigoUsuarioGerente": None,
                    "GerenteOficina": None,
                    "Cargo": None,
                },
            )
            for agencia in agencias_normalizadas
        ]

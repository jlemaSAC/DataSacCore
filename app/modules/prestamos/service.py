from app.modules.auth.schemas import AuthContext
from app.modules.prestamos.repositories.mongo_universo_repository import MongoUniversoPrestamosRepository
from app.modules.prestamos.schemas import (
    PrestamoUniverseRequest,
    UniversoPrestamosBuscarResponse,
    UniversoPrestamosConteos,
)


class UniversoPrestamosService:
    def __init__(
        self,
        repository: MongoUniversoPrestamosRepository | None = None,
    ) -> None:
        self.repository = repository

    def buscar_universo(
        self,
        filtros: PrestamoUniverseRequest,
        auth_context: AuthContext,
    ) -> UniversoPrestamosBuscarResponse:
        _ = auth_context
        if self.repository is None:
            raise RuntimeError("Repositorio Mongo de universo de prestamos no configurado.")

        actual = self.repository.get_actual_snapshots(filtros)
        historico = self.repository.get_historico_snapshots(filtros)

        return UniversoPrestamosBuscarResponse(
            actual=actual,
            historico=historico,
            conteos=UniversoPrestamosConteos(
                actual=len(actual),
                historico=len(historico),
            ),
        )

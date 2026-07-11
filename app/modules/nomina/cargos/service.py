from app.modules.auth.schemas import AuthContext
from app.modules.nomina.cargos.repositories.sql_cargo_repository import SqlCargoRepository
from app.modules.nomina.cargos.schemas import CargoResponse


class CargoService:
    def __init__(self, repository: SqlCargoRepository) -> None:
        self.repository = repository

    def list_cargos(
        self,
        auth_context: AuthContext,
        activo: bool | None = None,
    ) -> list[CargoResponse]:
        _ = auth_context
        return [
            CargoResponse.model_validate(cargo)
            for cargo in self.repository.list_cargos(activo=activo)
        ]

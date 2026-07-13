from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.modules.analytic.menu.repositories.mongo_menu_repository import (
    MongoMenuAnalyticAdminRepository,
)


def test_grupo_puede_tener_ruta() -> None:
    repository = MongoMenuAnalyticAdminRepository(MagicMock())

    repository._validar_documento_menu(
        {
            "tipo": "grupo",
            "ruta": "/analytic/indicadores-financieros",
        }
    )


def test_ruta_requiere_una_ruta() -> None:
    repository = MongoMenuAnalyticAdminRepository(MagicMock())

    with pytest.raises(HTTPException, match="debe tener ruta"):
        repository._validar_documento_menu({"tipo": "ruta", "ruta": None})

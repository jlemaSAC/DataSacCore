from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.core.settings import SettingsError
from app.db.session import check_database_connection

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/db")
def database_health_check() -> dict[str, str | int]:
    try:
        check_result = check_database_connection()
    except SettingsError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": "Base de datos no configurada",
                "detail": str(exc),
            },
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": "Base de datos no disponible",
                "detail": "No se pudo establecer conexion con SQL Server.",
            },
        ) from exc

    return {"status": "ok", "database": "connected", "check": check_result}

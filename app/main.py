import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pymongo.errors import PyMongoError
from sqlalchemy.exc import SQLAlchemyError

from app.core.settings import SettingsError, get_app_settings
from app.db.mongo import check_mongo_connection
from app.db.session import check_database_connection
from app.routers import health


logger = logging.getLogger("uvicorn.error")
logging.getLogger("watchfiles").setLevel(logging.WARNING)


def verify_database_on_startup() -> None:
    app_settings = get_app_settings()

    if not app_settings.check_database_on_startup:
        logger.warning("Verificacion de base de datos al iniciar desactivada")
        return

    try:
        check_result = check_database_connection()
    except (SettingsError, SQLAlchemyError) as exc:
        logger.exception("No se pudo conectar con la base de datos al iniciar")
        raise RuntimeError("No se pudo conectar con la base de datos al iniciar") from exc

    logger.info("Conexion con la base de datos establecida correctamente. Check=%s ✅​ ", check_result)


def verify_mongo_on_startup() -> None:
    app_settings = get_app_settings()

    if not app_settings.check_mongo_on_startup:
        logger.warning("Verificacion de MongoDB al iniciar desactivada")
        return

    try:
        check_result = check_mongo_connection()
    except (SettingsError, PyMongoError) as exc:
        logger.exception("No se pudo conectar con MongoDB al iniciar")
        raise RuntimeError("No se pudo conectar con MongoDB al iniciar") from exc

    logger.info("Conexion con MongoDB establecida correctamente. Check=%s ✅​", check_result)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    verify_database_on_startup()
    verify_mongo_on_startup()
    yield


settings = get_app_settings()
app = FastAPI(title=settings.name, version=settings.version, lifespan=lifespan)

app.include_router(health.router)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {"message": "Hello World"}

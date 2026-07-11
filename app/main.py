import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError
from sqlalchemy.exc import SQLAlchemyError

from app.core.settings import AppSettings, SettingsError, get_app_settings
from app.db.mongo import check_mongo_connection
from app.db.session import check_database_connection, check_secondary_database_connection
from app.modules.auth.router import router as auth_router
from app.modules.analytic.router import router as analytic_router
from app.modules.nomina.router import router as nomina_router
from app.modules.prestamos.router import router as prestamos_router
from app.modules.seguridad.router import router as seguridad_router
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


def verify_secondary_database_on_startup() -> None:
    app_settings = get_app_settings()

    if not app_settings.check_database_on_startup:
        logger.warning("Verificacion de base de datos secundaria al iniciar desactivada")
        return

    try:
        check_result = check_secondary_database_connection()
    except (SettingsError, SQLAlchemyError) as exc:
        logger.exception("No se pudo conectar con la base de datos secundaria al iniciar")
        raise RuntimeError("No se pudo conectar con la base de datos secundaria al iniciar") from exc

    logger.info(
        "Conexion con la base de datos secundaria establecida correctamente. Check=%s ✅​",
        check_result,
    )


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
    verify_secondary_database_on_startup()
    verify_mongo_on_startup()
    yield


def add_cors_middleware(fastapi_app: FastAPI, app_settings: AppSettings) -> None:
    allow_all_origins = "*" in app_settings.cors_allowed_origins

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.cors_allowed_origins),
        allow_credentials=not allow_all_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )


settings = get_app_settings()
app = FastAPI(title=settings.name, version=settings.version, lifespan=lifespan)

add_cors_middleware(app, settings)

app.include_router(health.router)
app.include_router(auth_router)
app.include_router(analytic_router)
app.include_router(nomina_router)
app.include_router(prestamos_router)
app.include_router(seguridad_router)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {"message": "Hello World"}

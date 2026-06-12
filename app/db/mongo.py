from functools import lru_cache

from pymongo import AsyncMongoClient, MongoClient
from pymongo.database import Database

from app.core.settings import get_mongo_settings


@lru_cache
def get_mongo_client_sync() -> MongoClient:
    settings = get_mongo_settings()
    return MongoClient(
        settings.uri,
        serverSelectionTimeoutMS=settings.server_selection_timeout_ms,
    )


@lru_cache
def get_mongo_client() -> AsyncMongoClient:
    settings = get_mongo_settings()
    return AsyncMongoClient(
        settings.uri,
        serverSelectionTimeoutMS=settings.server_selection_timeout_ms,
    )


def get_mongo_logs_db_sync() -> Database:
    return get_mongo_client_sync()[get_mongo_settings().logs_db]


def get_mongo_datasac_db_sync() -> Database:
    return get_mongo_client_sync()[get_mongo_settings().datasac_db]


def get_mongo_mayor_auxiliar_db_sync() -> Database:
    return get_mongo_client_sync()[get_mongo_settings().mayor_auxiliar_db]


def get_mongo_analytic_sac_db_sync() -> Database:
    return get_mongo_client_sync()[get_mongo_settings().analytic_sac_db]


def check_mongo_connection() -> int:
    result = get_mongo_client_sync().admin.command("ping")
    return int(result.get("ok", 0))

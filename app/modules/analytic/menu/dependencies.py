from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_analytic_sac_db_sync
from app.db.session import get_db
from app.modules.analytic.menu.repositories.mongo_menu_repository import (
    MongoMenuAnalyticAdminRepository,
)
from app.modules.analytic.menu.service import MenuAnalyticAdminService


def get_analytic_menu_service(
    db: Session = Depends(get_db),
) -> MenuAnalyticAdminService:
    repository = MongoMenuAnalyticAdminRepository(get_mongo_analytic_sac_db_sync())
    return MenuAnalyticAdminService(db=db, repository=repository)

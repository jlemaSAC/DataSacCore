from fastapi import APIRouter

from app.modules.seguridad.roles.router import router as roles_router


router = APIRouter(prefix="/seguridad")
router.include_router(roles_router)

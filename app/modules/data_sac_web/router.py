from fastapi import APIRouter

from app.modules.data_sac_web.auth.router import router as auth_router


router = APIRouter(prefix="/data-sac-web")
router.include_router(auth_router)

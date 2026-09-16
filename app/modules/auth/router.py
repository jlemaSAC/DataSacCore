from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.schemas import LoginResponse, UserLogin
from app.modules.auth.service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    return auth_service.login(login_data)

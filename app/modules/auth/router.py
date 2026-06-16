from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_auth_service, get_current_auth_context
from app.modules.auth.schemas import AuthContext, LoginResponse, UserLogin
from app.modules.auth.service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    return auth_service.login(login_data)


@router.get("/status", response_model=LoginResponse)
def status(
    auth_context: AuthContext = Depends(get_current_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    return auth_service.build_status_response(
        auth_context.usuario.sub,
        auth_context.usuario.fecha_sistema,
    )

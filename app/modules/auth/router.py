from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_auth_service, get_current_auth_context
from app.modules.auth.schemas import (
    AuthContext,
    LoginResponse,
    MenuAdminChild,
    MenuCompleteResponse,
    MenuDataSacWebCreateRequest,
    MenuDataSacWebUpdateRequest,
    MenuResponse,
    UserLogin,
)
from app.modules.auth.service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    return auth_service.login(login_data)


@router.get("/menu/data-sac-web", response_model=MenuResponse)
def menu(
    auth_context: AuthContext = Depends(get_current_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> MenuResponse:
    return auth_service.build_menu_response(auth_context.usuario.sub)


@router.get("/menu/data-sac-web/completo", response_model=MenuCompleteResponse)
def menu_completo_data_sac_web(
    auth_context: AuthContext = Depends(get_current_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> MenuCompleteResponse:
    return auth_service.build_complete_menu_response(auth_context.usuario.sub)


@router.post("/menu/data-sac-web", response_model=MenuAdminChild, status_code=201)
def crear_menu_data_sac_web(
    body: MenuDataSacWebCreateRequest,
    auth_context: AuthContext = Depends(get_current_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> MenuAdminChild:
    return auth_service.create_data_sac_web_menu_node(auth_context.usuario.sub, body)


@router.patch("/menu/data-sac-web/{id_menu}", response_model=MenuAdminChild)
def editar_menu_data_sac_web(
    id_menu: str,
    body: MenuDataSacWebUpdateRequest,
    auth_context: AuthContext = Depends(get_current_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> MenuAdminChild:
    return auth_service.update_data_sac_web_menu_node(auth_context.usuario.sub, id_menu, body)

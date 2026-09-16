from fastapi import APIRouter, Depends, Query

from app.modules.auth.dependencies import get_auth_service, get_current_auth_context
from app.modules.auth.schemas import (
    AuthContext,
    LoginResponse,
    MenuAdminChild,
    MenuCompleteResponse,
    MenuDataSacWebCreateRequest,
    MenuDataSacWebDeleteResponse,
    MenuDataSacWebUpdateRequest,
    MenuResponse,
    UserLogin,
)
from app.modules.auth.service import AuthService


router = APIRouter(prefix="/auth", tags=["DataSacWeb - Auth"])


@router.post("/login", response_model=LoginResponse)
def login_data_sac_web(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    return auth_service.login(login_data)


@router.get("/menu", response_model=MenuResponse)
def menu_data_sac_web(
    auth_context: AuthContext = Depends(get_current_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> MenuResponse:
    return auth_service.build_menu_response(auth_context.usuario.sub)


@router.get("/menu/completo", response_model=MenuCompleteResponse)
def menu_completo_data_sac_web(
    activo: bool | None = Query(default=None),
    auth_context: AuthContext = Depends(get_current_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> MenuCompleteResponse:
    return auth_service.build_complete_menu_response(auth_context.usuario.sub, activo=activo)


@router.get("/menu/{id_menu}", response_model=MenuAdminChild)
def obtener_menu_data_sac_web(
    id_menu: str,
    auth_context: AuthContext = Depends(get_current_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> MenuAdminChild:
    return auth_service.get_data_sac_web_menu_node(auth_context.usuario.sub, id_menu)


@router.post("/menu", response_model=MenuAdminChild, status_code=201)
def crear_menu_data_sac_web(
    body: MenuDataSacWebCreateRequest,
    auth_context: AuthContext = Depends(get_current_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> MenuAdminChild:
    return auth_service.create_data_sac_web_menu_node(auth_context.usuario.sub, body)


@router.patch("/menu/{id_menu}", response_model=MenuAdminChild)
def editar_menu_data_sac_web(
    id_menu: str,
    body: MenuDataSacWebUpdateRequest,
    auth_context: AuthContext = Depends(get_current_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> MenuAdminChild:
    return auth_service.update_data_sac_web_menu_node(auth_context.usuario.sub, id_menu, body)


@router.delete("/menu/{id_menu}", response_model=MenuDataSacWebDeleteResponse)
def eliminar_menu_data_sac_web(
    id_menu: str,
    auth_context: AuthContext = Depends(get_current_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> MenuDataSacWebDeleteResponse:
    return auth_service.delete_data_sac_web_menu_node(auth_context.usuario.sub, id_menu)

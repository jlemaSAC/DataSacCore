from fastapi import APIRouter, Depends

from app.modules.analytic.menu.dependencies import get_analytic_menu_service
from app.modules.analytic.menu.schemas import (
    MenuAnalyticAdminResponse,
    MenuAnalyticAdminTreeResponse,
    MenuAnalyticCreateRequest,
    MenuAnalyticDeleteResponse,
    MenuAnalyticResponse,
    MenuAnalyticUpdateRequest,
    PermisoAnalyticAdminResponse,
    PermisoAnalyticCreateRequest,
    RolPermisoAnalyticAdminResponse,
    RolPermisoAnalyticCreateRequest,
)
from app.modules.analytic.menu.service import MenuAnalyticAdminService
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter()


@router.get(
    "/menu",
    response_model=list[MenuAnalyticResponse],
    summary="Obtener menu autorizado de Analytic Sac",
    tags=["Analytic Sac"],
)
def listar_menu(
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: MenuAnalyticAdminService = Depends(get_analytic_menu_service),
) -> list[MenuAnalyticResponse]:
    return service.get_menu(auth_context)


@router.get(
    "/rutas",
    response_model=list[MenuAnalyticAdminResponse],
    summary="Listar rutas y grupos del menu Analytic Sac",
    tags=["Analytic Sac - Admin"],
)
def listar_rutas_menu(
    activo: bool | None = None,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: MenuAnalyticAdminService = Depends(get_analytic_menu_service),
) -> list[MenuAnalyticAdminResponse]:
    return service.list_menu_routes(auth_context, activo=activo)


@router.post(
    "/rutas",
    response_model=MenuAnalyticAdminResponse,
    status_code=201,
    summary="Crear grupo o ruta del menu Analytic Sac",
    tags=["Analytic Sac - Admin"],
)
def crear_ruta_menu(
    body: MenuAnalyticCreateRequest,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: MenuAnalyticAdminService = Depends(get_analytic_menu_service),
) -> MenuAnalyticAdminResponse:
    return service.create_menu_route(auth_context, body)


@router.get(
    "/rutas/arbol",
    response_model=list[MenuAnalyticAdminTreeResponse],
    summary="Listar arbol completo del menu Analytic Sac",
    tags=["Analytic Sac - Admin"],
)
def listar_arbol_rutas_menu(
    activo: bool | None = None,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: MenuAnalyticAdminService = Depends(get_analytic_menu_service),
) -> list[MenuAnalyticAdminTreeResponse]:
    return service.list_menu_tree(auth_context, activo=activo)


@router.get(
    "/rutas/{id_menu}",
    response_model=MenuAnalyticAdminResponse,
    summary="Obtener ruta o grupo del menu Analytic Sac",
    tags=["Analytic Sac - Admin"],
)
def obtener_ruta_menu(
    id_menu: str,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: MenuAnalyticAdminService = Depends(get_analytic_menu_service),
) -> MenuAnalyticAdminResponse:
    return service.get_menu_route(auth_context, id_menu)


@router.patch(
    "/rutas/{id_menu}",
    response_model=MenuAnalyticAdminResponse,
    summary="Editar ruta o grupo del menu Analytic Sac",
    tags=["Analytic Sac - Admin"],
)
def editar_ruta_menu(
    id_menu: str,
    body: MenuAnalyticUpdateRequest,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: MenuAnalyticAdminService = Depends(get_analytic_menu_service),
) -> MenuAnalyticAdminResponse:
    return service.update_menu_route(auth_context, id_menu, body)


@router.delete(
    "/rutas/{id_menu}",
    response_model=MenuAnalyticDeleteResponse,
    summary="Eliminar ruta o grupo del menu Analytic Sac",
    tags=["Analytic Sac - Admin"],
)
def eliminar_ruta_menu(
    id_menu: str,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: MenuAnalyticAdminService = Depends(get_analytic_menu_service),
) -> MenuAnalyticDeleteResponse:
    return service.delete_menu_route(auth_context, id_menu)


@router.post(
    "/permisos",
    response_model=PermisoAnalyticAdminResponse,
    status_code=201,
    summary="Crear permiso del menu Analytic Sac",
    tags=["Analytic Sac - Admin"],
)
def crear_permiso(
    body: PermisoAnalyticCreateRequest,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: MenuAnalyticAdminService = Depends(get_analytic_menu_service),
) -> PermisoAnalyticAdminResponse:
    return service.create_permission(auth_context, body)


@router.post(
    "/rol-permisos",
    response_model=RolPermisoAnalyticAdminResponse,
    status_code=201,
    summary="Asignar permiso a rol para el menu Analytic Sac",
    tags=["Analytic Sac - Admin"],
)
def crear_rol_permiso(
    body: RolPermisoAnalyticCreateRequest,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: MenuAnalyticAdminService = Depends(get_analytic_menu_service),
) -> RolPermisoAnalyticAdminResponse:
    return service.create_role_permission(auth_context, body)

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.schemas import AuthContext
from app.modules.auth.security import JwtTokenService, TokenValidationError
from app.modules.auth.service import AuthService


bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_current_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="No se encontro un token valido en la solicitud")

    try:
        usuario = JwtTokenService().decode_access_token(credentials.credentials)
    except TokenValidationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    auth_context = AuthContext.from_token_payload(credentials.credentials, usuario)
    request.state.codigo_usuario = auth_context.usuario.sub
    return auth_context

import base64
import hashlib
from datetime import date, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError

from app.core.settings import get_jwt_settings
from app.models.seguridad.usuario_model import Usuario
from app.modules.auth.schemas import UsuarioTokenPayload


class TokenValidationError(ValueError):
    pass


class PasswordHasher:
    def generate_hash(self, codigo: str, clave: str) -> str:
        sha1_hash = hashlib.sha1(f"{codigo}{clave}".encode("utf-8")).digest()
        return base64.b64encode(sha1_hash).decode("utf-8")


class JwtTokenService:
    def create_access_token(
        self,
        usuario: Usuario,
        fecha_sistema: date | datetime,
        nombre_agencia: str,
    ) -> str:
        settings = get_jwt_settings()
        now = datetime.now()
        expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
        payload = {
            "sub": usuario.usuario,
            "usuario": usuario.nombre,
            "id_agencia": usuario.id_agencia,
            "nombre_agencia": nombre_agencia,
            "fecha_sistema": fecha_sistema.isoformat(),
            "iat": now.timestamp(),
            "exp": expires_at.timestamp(),
        }
        return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    def decode_access_token(self, token: str) -> UsuarioTokenPayload:
        settings = get_jwt_settings()
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm],
            )
        except InvalidTokenError as exc:
            raise TokenValidationError("Token invalido") from exc

        return UsuarioTokenPayload.model_validate(payload)

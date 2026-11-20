from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.usuario import Usuario


class AuthenticationError(Exception):
    """Error cuando las credenciales no son válidas."""


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> tuple[str, int]:
    """Valida las credenciales y devuelve un JWT y su duración en segundos."""

    user = db.scalar(select(Usuario).where(Usuario.correo == email.strip().lower()))

    if user is None or not verify_password(password, user.contrasena):
        raise AuthenticationError("Correo electrónico o contraseña incorrectos.")

    if user.estado != "Activo":
        raise AuthenticationError("Correo electrónico o contraseña incorrectos.")

    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(
        {
            "sub": str(user.idUsuario),
            "jti": str(uuid4()),
        }
    )

    return access_token, expires_in

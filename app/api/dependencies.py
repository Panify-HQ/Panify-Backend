import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import verify_access_token
from app.infrastructure.database.session import get_db
from app.models.revoked_token import RevokedToken
from app.models.usuario import Usuario

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autorizado. Inicia sesión nuevamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = verify_access_token(credentials.credentials)
        user_id = int(payload["sub"])
        jti = payload["jti"]
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise unauthorized

    if db.get(RevokedToken, jti) is not None:
        raise unauthorized

    user = db.get(Usuario, user_id)
    if user is None or user.estado != "Activo":
        raise unauthorized

    return user

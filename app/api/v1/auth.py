from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import bearer_scheme, get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    verify_access_token,
    verify_password,
)
from app.infrastructure.database.session import get_db
from app.models.revoked_token import RevokedToken
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


class AuthenticationError(Exception):
    pass


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> tuple[str, int]:
    user = db.scalar(
        select(Usuario).where(Usuario.correo == email.strip().lower())
    )

    if user is None or not verify_password(password, user.contrasena):
        raise AuthenticationError

    if user.estado != "Activo":
        raise AuthenticationError

    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(
        {
            "sub": str(user.idUsuario),
            "jti": str(uuid4()),
        }
    )
    return access_token, expires_in


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Autentica al usuario y devuelve un JWT."""

    try:
        access_token, expires_in = authenticate_user(
            db=db,
            email=str(data.email),
            password=data.password,
        )
    except AuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos.",
        ) from error

    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Devuelve el perfil del usuario autenticado."""

    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Revoca el JWT actual para que no pueda volver a utilizarse."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_access_token(credentials.credentials)
    jti = payload["jti"]
    expires_at = datetime.fromtimestamp(
        payload["exp"],
        tz=timezone.utc,
    ).replace(tzinfo=None)

    db.add(RevokedToken(jti=jti, expires_at=expires_at))
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)

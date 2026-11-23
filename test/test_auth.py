from datetime import datetime

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.v1.auth import AuthenticationError, authenticate_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_access_token
from app.infrastructure.database.base import Base
from app.models.revoked_token import RevokedToken
from app.models.roles import Rol
from app.models.usuario import Usuario


def create_database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            RevokedToken.__table__,
            Rol.__table__,
            Usuario.__table__,
        ],
    )
    return engine


def add_user(db: Session, state: str = "Activo") -> Usuario:
    db.add(Rol(idRol=1, nombre="Cliente"))
    db.flush()
    user = Usuario(
        nombre="Ana",
        apellido="Lopez",
        correo="ana@example.com",
        contrasena=hash_password("ClaveSegura12"),
        telefono="3001234567",
        estado=state,
        Rol_idRol=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_authenticate_user_returns_a_valid_access_token(monkeypatch):
    engine = create_database()
    monkeypatch.setattr(
        settings,
        "JWT_SECRET_KEY",
        "test-secret-key-for-jwt-signing-32",
    )

    with Session(engine) as db:
        user = add_user(db)

        access_token, expires_in = authenticate_user(
            db,
            " ANA@example.com ",
            "ClaveSegura12",
        )

        assert verify_access_token(access_token)["sub"] == str(user.idUsuario)
        assert verify_access_token(access_token)["jti"]
        assert expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


@pytest.mark.parametrize(
    ("state", "password"),
    [("Inactivo", "ClaveSegura12"), ("Activo", "ContraseñaIncorrecta")],
)
def test_authenticate_user_rejects_inactive_user_or_wrong_password(state, password):
    engine = create_database()

    with Session(engine) as db:
        add_user(db, state)

        with pytest.raises(AuthenticationError):
            authenticate_user(db, "ana@example.com", password)


def test_get_current_user_rejects_invalid_access_token():
    engine = create_database()

    with Session(engine) as db:
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid-token",
        )

        with pytest.raises(HTTPException) as error:
            get_current_user(credentials, db)

        assert error.value.status_code == 401


def test_get_current_user_rejects_revoked_access_token(monkeypatch):
    engine = create_database()
    monkeypatch.setattr(
        settings,
        "JWT_SECRET_KEY",
        "test-secret-key-for-jwt-signing-32",
    )

    with Session(engine) as db:
        user = add_user(db)
        token_id = "revoked-token-id"
        token = create_access_token({"sub": str(user.idUsuario), "jti": token_id})
        db.add(
            RevokedToken(
                jti=token_id,
                expires_at=datetime.now(),
            )
        )
        db.commit()
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        with pytest.raises(HTTPException) as error:
            get_current_user(credentials, db)

        assert error.value.status_code == 401

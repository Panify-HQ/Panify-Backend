from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.v1.auth import logout
from app.core.security import create_access_token, hash_password
from app.infrastructure.database.base import Base
from app.models.revoked_token import RevokedToken
from app.models.roles import Rol
from app.models.usuario import Usuario


def authorization_for(jti: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=create_access_token({"sub": "27", "jti": jti}),
    )


def test_current_user_loads_panify_usuario_and_checks_revocation():
    user = SimpleNamespace(idUsuario=27, estado="Activo")
    db = Mock()
    db.get.side_effect = lambda model, key: (
        None if model is RevokedToken else user
    )

    current_user = get_current_user(authorization_for("jti-27"), db)

    assert current_user is user
    assert db.get.call_args_list == [
        call(RevokedToken, "jti-27"),
        call(Usuario, 27),
    ]


@pytest.mark.parametrize(
    ("credentials", "user"),
    [
        (None, None),
        (authorization_for("missing-user"), None),
        (authorization_for("inactive-user"), SimpleNamespace(estado="Inactivo")),
    ],
)
def test_current_user_rejects_missing_or_inactive_users(credentials, user):
    db = Mock()
    db.get.side_effect = lambda model, key: (
        None if model is RevokedToken else user
    )

    with pytest.raises(HTTPException) as error:
        get_current_user(credentials, db)

    assert error.value.status_code == 401


def test_current_user_rejects_revoked_token():
    user = SimpleNamespace(idUsuario=27, estado="Activo")
    revoked_token = SimpleNamespace(jti="revoked-jti")
    db = Mock()
    db.get.side_effect = lambda model, key: (
        revoked_token if model is RevokedToken else user
    )

    with pytest.raises(HTTPException) as error:
        get_current_user(authorization_for("revoked-jti"), db)

    assert error.value.status_code == 401
    db.get.assert_called_once_with(RevokedToken, "revoked-jti")


def test_logout_persists_revocation_and_blocks_the_same_token():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[Rol.__table__, Usuario.__table__, RevokedToken.__table__],
    )

    with Session(engine) as db:
        db.add(Rol(idRol=5, nombre="Cliente"))
        db.flush()
        user = Usuario(
            nombre="Ana",
            apellido="Lopez",
            correo="ana@example.com",
            contrasena=hash_password("ClaveSegura12"),
            telefono="3001234567",
            estado="Activo",
            Rol_idRol=5,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=create_access_token(
                {"sub": str(user.idUsuario), "jti": "logout-jti"}
            ),
        )
        current_user = get_current_user(credentials, db)

        response = logout(credentials, current_user, db)

        assert response.status_code == 204
        revoked_token = db.get(RevokedToken, "logout-jti")
        assert revoked_token is not None
        assert isinstance(revoked_token.expires_at, datetime)

        with pytest.raises(HTTPException) as error:
            get_current_user(credentials, db)

        assert error.value.status_code == 401

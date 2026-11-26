from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.security import hash_password, verify_access_token
from app.api.v1.auth import AuthenticationError, authenticate_user


def make_user(**overrides):
    user = {
        "idUsuario": 12,
        "correo": "ana@example.com",
        "contrasena": hash_password("ClaveSegura12"),
        "estado": "Activo",
    }
    user.update(overrides)
    return SimpleNamespace(**user)


def test_authenticate_user_returns_jwt_without_persisting_session():
    db = Mock()
    db.scalar.return_value = make_user()

    token, expires_in = authenticate_user(
        db,
        email=" Ana@Example.com ",
        password="ClaveSegura12",
    )

    payload = verify_access_token(token)
    assert payload["sub"] == "12"
    assert payload["jti"]
    assert expires_in > 0
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize(
    ("user", "password"),
    [
        (None, "ClaveSegura12"),
        (make_user(), "OtraClave"),
        (make_user(estado="Inactivo"), "ClaveSegura12"),
    ],
)
def test_authenticate_user_rejects_invalid_credentials_or_inactive_user(user, password):
    db = Mock()
    db.scalar.return_value = user

    with pytest.raises(AuthenticationError):
        authenticate_user(db, email="ana@example.com", password=password)

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1 import users
from app.schemas.user import UserUpdate, UsuarioEstadoActualizar


def test_user_routes_use_english_prefix():
    paths = {route.path for route in users.router.routes}

    assert {
        "/users/",
        "/users/{user_id}",
        "/users/{user_id}/status",
    }.issubset(paths)
    assert not any(path.startswith("/usuarios") for path in paths)


def test_user_management_requires_superadmin():
    superadmin = SimpleNamespace(rol=SimpleNamespace(nombre="Superadmin"))

    assert users.require_super_admin(superadmin) is superadmin

    with pytest.raises(HTTPException) as error:
        users.require_super_admin(
            SimpleNamespace(rol=SimpleNamespace(nombre="Cliente"))
        )

    assert error.value.status_code == 403


def test_update_user_passes_authenticated_user_to_service(monkeypatch):
    db = Mock()
    current_user = SimpleNamespace(idUsuario=42)
    data = UserUpdate(nombre="Ana")
    expected_user = object()
    update_user = Mock(return_value=expected_user)
    monkeypatch.setattr(users.UserService, "update_user", update_user)

    response = users.update_user(
        user_id=17,
        data=data,
        db=db,
        current_user=current_user,
    )

    assert response is expected_user
    update_user.assert_called_once_with(
        db,
        17,
        data,
        current_user=current_user,
    )


@pytest.mark.parametrize(
    ("state", "is_active"),
    [("Activo", True), ("Inactivo", False)],
)
def test_status_endpoint_maps_project_state_to_service_flag(
    monkeypatch, state, is_active
):
    db = Mock()
    current_user = SimpleNamespace(idUsuario=42)
    expected_user = object()
    change_status = Mock(return_value=expected_user)
    monkeypatch.setattr(users.UserService, "change_status", change_status)

    response = users.change_user_status(
        user_id=17,
        data=UsuarioEstadoActualizar(estado=state),
        db=db,
        current_user=current_user,
    )

    assert response is expected_user
    change_status.assert_called_once_with(
        db=db,
        user_id=17,
        is_active=is_active,
        current_user_id=42,
    )


def test_status_schema_rejects_unknown_account_states():
    with pytest.raises(ValidationError):
        UsuarioEstadoActualizar(estado="Suspendido")

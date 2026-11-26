from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1 import users as users_api
from app.infrastructure.database.base import Base
from app.models.cliente import Cliente
from app.models.domiciliario import Domiciliario
from app.models.panaderos import Panadero
from app.models.roles import Rol
from app.models.usuario import Usuario
from app.schemas.user import UserRole, UsuarioCrear, UsuarioRespuesta
from app.services.user_service import UserService
from app.api.v1.users import registrar_usuario


def valid_registration_data(**overrides):
    data = {
        "nombre": "Ana",
        "apellido": "Lopez",
        "correo": "ana@example.com",
        "contrasena": "ClaveSegura12",
        "telefono": "3001234567",
        "direccion": "Calle 1 # 2-3",
    }
    data.update(overrides)
    return data


def test_registration_schema_accepts_field_limits_and_colombian_phone():
    usuario = UsuarioCrear(
        **valid_registration_data(
            nombre="N" * 45,
            apellido="A" * 45,
            telefono="+573001234567",
            direccion="D" * 150,
        )
    )

    assert len(usuario.nombre) == 45
    assert len(usuario.apellido) == 45
    assert len(usuario.direccion) == 150


@pytest.mark.parametrize(
    "overrides",
    [
        {"nombre": "N" * 46},
        {"apellido": "A" * 46},
        {"telefono": "300123456A"},
        {"telefono": "300123456"},
        {"telefono": "+57300123456"},
        {"direccion": "D" * 151},
    ],
)
def test_registration_schema_rejects_invalid_fields(overrides):
    with pytest.raises(ValidationError):
        UsuarioCrear(**valid_registration_data(**overrides))


def test_registration_creates_customer_with_delivery_address():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[Cliente.__table__, Rol.__table__, Usuario.__table__],
    )

    with Session(engine) as db:
        db.add(Rol(idRol=1, nombre="Cliente"))
        db.commit()

        usuario = UserService.create_user(
            db,
            UsuarioCrear(**valid_registration_data()),
        )

        cliente = db.get(Cliente, usuario.cliente_idCliente)
        assert cliente is not None
        assert usuario.cliente_idCliente == cliente.idCliente
        assert cliente.tipoCliente == "Nuevo"
        assert cliente.direccion == "Calle 1 # 2-3"
        assert usuario.contrasena != "ClaveSegura12"
        assert UsuarioRespuesta.model_validate(usuario).direccion == cliente.direccion


def test_registration_assigns_cliente_role_by_name():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[Cliente.__table__, Rol.__table__, Usuario.__table__],
    )

    with Session(engine) as db:
        db.add_all(
            [
                Rol(idRol=1, nombre="Superadmin"),
                Rol(idRol=2, nombre="Administrador"),
                Rol(idRol=3, nombre="Panadero"),
                Rol(idRol=4, nombre="Domiciliario"),
                Rol(idRol=5, nombre="Cliente"),
            ]
        )
        db.commit()

        usuario = registrar_usuario(
            UsuarioCrear(**valid_registration_data()),
            db,
        )

        assert usuario.Rol_idRol == 5


@pytest.mark.parametrize(
    ("role", "profile"),
    [
        ("Panadero", {"perfil_panadero": {"estadoActividad": "En Turno"}}),
        (
            "Domiciliario",
            {"perfil_domiciliario": {"estadoDisponibilidad": "Libre"}},
        ),
    ],
)
def test_registration_schema_accepts_current_staff_roles(role, profile):
    usuario = UsuarioCrear(**valid_registration_data(rol=role, **profile))

    assert usuario.rol.value == role


def test_registration_schema_rejects_superadmin_and_unknown_roles():
    with pytest.raises(ValidationError, match="Superadmin"):
        UsuarioCrear(**valid_registration_data(rol="Superadmin"))

    with pytest.raises(ValidationError):
        UsuarioCrear(**valid_registration_data(rol="Esteticista"))


def test_user_role_values_match_roles_seeded_by_the_project():
    assert [role.value for role in UserRole] == [
        "Superadmin",
        "Administrador",
        "Panadero",
        "Domiciliario",
        "Cliente",
    ]


@pytest.mark.parametrize(
    ("role", "profile", "profile_model", "profile_id", "state"),
    [
        (
            "Panadero",
            {"perfil_panadero": {"estadoActividad": "En Turno"}},
            Panadero,
            "panadero_idPanadero",
            "estadoActividad",
        ),
        (
            "Domiciliario",
            {"perfil_domiciliario": {"estadoDisponibilidad": "Libre"}},
            Domiciliario,
            "domiciliario_idDomiciliario",
            "estadoDisponibilidad",
        ),
    ],
)
def test_registration_creates_role_specific_profile(
    role, profile, profile_model, profile_id, state
):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[profile_model.__table__, Rol.__table__, Usuario.__table__],
    )

    with Session(engine) as db:
        db.add(Rol(idRol=1, nombre=role))
        db.commit()
        usuario = UserService.create_user(
            db,
            UsuarioCrear(**valid_registration_data(rol=role, **profile)),
        )

        perfil = db.get(profile_model, getattr(usuario, profile_id))
        assert perfil is not None
        profile_pk = {
            "Panadero": "idPanadero",
            "Domiciliario": "idDomiciliario",
        }[role]
        assert getattr(usuario, profile_id) == getattr(perfil, profile_pk)
        expected_state = next(iter(profile.values()))[state]
        assert getattr(perfil, state) == expected_state


def test_registration_requires_authentication_for_staff_roles():
    datos = UsuarioCrear(
        **valid_registration_data(
            rol="Panadero",
            perfil_panadero={"estadoActividad": "En Turno"},
        )
    )

    with pytest.raises(HTTPException) as error:
        registrar_usuario(datos, Mock(), None)

    assert error.value.status_code == 401


def test_administrator_can_register_panadero_with_profile(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[Panadero.__table__, Rol.__table__, Usuario.__table__],
    )
    monkeypatch.setattr(
        users_api,
        "get_current_user",
        lambda credentials, db: SimpleNamespace(
            rol=SimpleNamespace(nombre="Administrador")
        ),
    )

    with Session(engine) as db:
        db.add(Rol(idRol=1, nombre="Panadero"))
        db.commit()
        usuario = users_api.registrar_usuario(
            UsuarioCrear(
                **valid_registration_data(
                    rol="Panadero",
                    perfil_panadero={"estadoActividad": "En Turno"},
                )
            ),
            db,
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"),
        )

        panadero = db.get(Panadero, usuario.panadero_idPanadero)
        assert panadero is not None
        assert panadero.estadoActividad == "En Turno"


def test_administrator_cannot_register_another_administrator(monkeypatch):
    monkeypatch.setattr(
        users_api,
        "get_current_user",
        lambda credentials, db: SimpleNamespace(
            rol=SimpleNamespace(nombre="Administrador")
        ),
    )

    with pytest.raises(HTTPException) as error:
        users_api.registrar_usuario(
            UsuarioCrear(**valid_registration_data(rol="Administrador")),
            Mock(),
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"),
        )

    assert error.value.status_code == 403

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.database.base import Base
from app.models.cliente import Cliente
from app.models.domiciliario import Domiciliario
from app.models.panaderos import Panadero
from app.models.roles import Rol
from app.models.usuario import Usuario
from app.schemas.user import UserRole, UserUpdate, UsuarioCrear
from app.services.user_service import (
    UserNotFoundError,
    UserService,
    UserServiceError,
)


def create_database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            Cliente.__table__,
            Domiciliario.__table__,
            Panadero.__table__,
            Rol.__table__,
            Usuario.__table__,
        ],
    )
    return engine


def add_roles(db):
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


def customer_data(**overrides):
    data = {
        "nombre": "Ana",
        "apellido": "Lopez",
        "correo": "ana@example.com",
        "contrasena": "ClaveSegura12",
        "telefono": "3001234567",
        "direccion": "Calle 1",
        "rol": UserRole.CLIENTE,
    }
    data.update(overrides)
    return UsuarioCrear(**data)


def test_user_service_creates_and_lists_project_user():
    engine = create_database()

    with Session(engine) as db:
        add_roles(db)
        user = UserService.create_user(db, customer_data())

        assert user.nombre == "Ana"
        assert user.rol.nombre == "Cliente"
        cliente = db.get(Cliente, user.cliente_idCliente)
        assert cliente is not None
        assert cliente.direccion == "Calle 1"
        assert UserService.list_users(db, role=UserRole.CLIENTE) == [user]


def test_user_service_updates_model_fields_and_customer_address():
    engine = create_database()

    with Session(engine) as db:
        add_roles(db)
        user = UserService.create_user(db, customer_data())

        updated = UserService.update_user(
            db,
            user.idUsuario,
            UserUpdate(
                nombre=" Ana María ",
                correo="ana.nueva@example.com",
                direccion=" Carrera 2 ",
            ),
        )

        assert updated.nombre == "Ana María"
        assert updated.correo == "ana.nueva@example.com"
        cliente = db.get(Cliente, updated.cliente_idCliente)
        assert cliente is not None
        assert cliente.direccion == "Carrera 2"


def test_user_service_rejects_missing_users_and_self_deactivation():
    engine = create_database()

    with Session(engine) as db:
        add_roles(db)
        user = UserService.create_user(db, customer_data())

        with pytest.raises(UserNotFoundError):
            UserService.get_user(db, 999)

        with pytest.raises(UserServiceError, match="desactivar tu propia cuenta"):
            UserService.change_status(
                db,
                user.idUsuario,
                is_active=False,
                current_user_id=user.idUsuario,
            )

        assert user.estado == "Activo"

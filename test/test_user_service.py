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
    UserPermissionError,
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


def add_superadmin(db):
    user = Usuario(
        nombre="Sofia",
        apellido="Admin",
        correo="superadmin@example.com",
        contrasena="hashed-password",
        telefono="3001234568",
        estado="Activo",
        Rol_idRol=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
            current_user=user,
        )

        assert updated.nombre == "Ana María"
        assert updated.correo == "ana.nueva@example.com"
        cliente = db.get(Cliente, updated.cliente_idCliente)
        assert cliente is not None
        assert cliente.direccion == "Carrera 2"


def test_user_service_changes_role_and_preserves_existing_profiles():
    engine = create_database()

    with Session(engine) as db:
        add_roles(db)
        user = UserService.create_user(db, customer_data())
        superadmin = add_superadmin(db)
        assert user.direccion == "Calle 1"

        updated = UserService.update_user(
            db,
            user.idUsuario,
            UserUpdate(rol=UserRole.PANADERO),
            current_user=superadmin,
        )

        assert updated.rol.nombre == UserRole.PANADERO.value
        assert updated.direccion is None
        assert updated.cliente_idCliente is None
        assert updated.panadero_idPanadero == user.idUsuario
        assert db.get(Cliente, user.idUsuario) is not None
        assert db.get(Panadero, user.idUsuario).estadoActividad == "Inactivo"

        updated = UserService.update_user(
            db,
            user.idUsuario,
            UserUpdate(rol=UserRole.CLIENTE),
            current_user=superadmin,
        )

        assert updated.rol.nombre == UserRole.CLIENTE.value
        assert updated.cliente_idCliente == user.idUsuario
        assert updated.panadero_idPanadero is None
        assert db.get(Cliente, user.idUsuario).direccion == "Calle 1"

        updated = UserService.update_user(
            db,
            user.idUsuario,
            UserUpdate(rol=UserRole.DOMICILIARIO),
            current_user=superadmin,
        )

        assert updated.rol.nombre == UserRole.DOMICILIARIO.value
        assert updated.cliente_idCliente is None
        assert updated.domiciliario_idDomiciliario == user.idUsuario
        assert db.get(Domiciliario, user.idUsuario).estadoDisponibilidad == "Libre"

        updated = UserService.update_user(
            db,
            user.idUsuario,
            UserUpdate(rol=UserRole.ADMINISTRADOR),
            current_user=superadmin,
        )

        assert updated.rol.nombre == UserRole.ADMINISTRADOR.value
        assert updated.cliente_idCliente is None
        assert updated.panadero_idPanadero is None
        assert updated.domiciliario_idDomiciliario is None
        assert db.get(Cliente, user.idUsuario) is not None


def test_user_service_requires_address_when_creating_customer_profile():
    engine = create_database()

    with Session(engine) as db:
        add_roles(db)
        user = UserService.create_user(
            db,
            customer_data(
                correo="panadero@example.com",
                rol=UserRole.PANADERO,
                direccion=None,
                perfil_panadero={"estadoActividad": "Inactivo"},
            ),
        )
        superadmin = add_superadmin(db)

        with pytest.raises(UserServiceError, match="proporcionar una dirección"):
            UserService.update_user(
                db,
                user.idUsuario,
                UserUpdate(rol=UserRole.CLIENTE),
                current_user=superadmin,
            )

        assert user.rol.nombre == UserRole.PANADERO.value
        assert user.cliente_idCliente is None


def test_user_service_rejects_promoting_user_to_superadmin():
    engine = create_database()

    with Session(engine) as db:
        add_roles(db)
        user = UserService.create_user(db, customer_data())
        superadmin = add_superadmin(db)

        with pytest.raises(UserServiceError, match="asignar el rol Superadmin"):
            UserService.update_user(
                db,
                user.idUsuario,
                UserUpdate(rol=UserRole.SUPERADMIN),
                current_user=superadmin,
            )

        assert user.rol.nombre == UserRole.CLIENTE.value


def test_user_service_rejects_non_admin_updating_another_user():
    engine = create_database()

    with Session(engine) as db:
        add_roles(db)
        target = UserService.create_user(db, customer_data())
        actor = UserService.create_user(
            db,
            customer_data(correo="otra@example.com"),
        )

        with pytest.raises(UserPermissionError, match="otro usuario"):
            UserService.update_user(
                db,
                target.idUsuario,
                UserUpdate(nombre="Cambio"),
                current_user=actor,
            )


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

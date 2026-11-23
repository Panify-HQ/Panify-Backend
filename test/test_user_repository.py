from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.database.base import Base
from app.models.roles import Rol
from app.models.usuario import Usuario
from app.repositories.user_repository import UserRepository


def test_user_repository_uses_panify_user_fields_and_role_names():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[Rol.__table__, Usuario.__table__],
    )

    with Session(engine) as db:
        db.add_all(
            [
                Rol(idRol=1, nombre="Cliente"),
                Rol(idRol=2, nombre="Administrador"),
            ]
        )
        db.flush()
        customer = Usuario(
            nombre="Ana",
            apellido="Lopez",
            correo="ana@example.com",
            contrasena="hashed-password",
            telefono="3001234567",
            estado="Activo",
            Rol_idRol=1,
        )
        inactive_admin = Usuario(
            nombre="Luis",
            apellido="Perez",
            correo="luis@example.com",
            contrasena="hashed-password",
            telefono="3001234568",
            estado="Inactivo",
            Rol_idRol=2,
        )
        db.add_all([customer, inactive_admin])
        db.commit()

        assert UserRepository.get_by_id(db, customer.idUsuario) is customer
        assert UserRepository.get_by_email(db, " ANA@example.com ") is customer
        assert UserRepository.list_users(db, role="Cliente", is_active=True) == [
            customer
        ]
        assert UserRepository.list_users(db, is_active=False) == [inactive_admin]

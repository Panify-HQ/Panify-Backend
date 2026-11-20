import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.database.base import Base
from app.models.cliente import Cliente
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCrear
from app.services.usuario_service import crear_usuario
from app.api.v1.usuarios import registrar_usuario


def valid_registration_data(**overrides):
    data = {
        "nombre": "Ana",
        "apellido": "Lopez",
        "correo": "ana@example.com",
        "contrasena": "Clave123",
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

        usuario = crear_usuario(
            db=db,
            nombre="Ana",
            apellido="Lopez",
            correo="ana@example.com",
            contrasena="Clave123",
            telefono="3001234567",
            direccion="Calle 1 # 2-3",
            rol_id=1,
        )

        cliente = db.get(Cliente, usuario.cliente_idCliente)
        assert cliente is not None
        assert cliente.idCliente == usuario.idUsuario
        assert cliente.tipoCliente == "Nuevo"
        assert cliente.direccion == "Calle 1 # 2-3"
        assert usuario.contrasena != "Clave123"


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

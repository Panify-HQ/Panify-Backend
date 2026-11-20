import pytest

from app.core.security import hash_password, verify_password
from app.schemas.usuario import UsuarioCrear


def test_hash_password_accepts_eight_characters():
    hashed_password = hash_password("Clave123")

    assert verify_password("Clave123", hashed_password)


def test_hash_password_rejects_fewer_than_eight_characters():
    with pytest.raises(ValueError, match="al menos 8 caracteres"):
        hash_password("Clave12")


def test_usuario_schema_requires_eight_character_password():
    user_data = {
        "nombre": "Ana",
        "apellido": "Lopez",
        "correo": "ana@example.com",
        "telefono": "3001234567",
        "direccion": "Calle 1 # 2-3",
    }

    with pytest.raises(ValueError):
        UsuarioCrear(**user_data, contrasena="Clave12")

    usuario = UsuarioCrear(**user_data, contrasena="Clave123")
    assert usuario.contrasena == "Clave123"

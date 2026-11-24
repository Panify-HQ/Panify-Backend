from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserRole(str, Enum):
    SUPERADMIN = "Superadmin"
    ADMINISTRADOR = "Administrador"
    PANADERO = "Panadero"
    DOMICILIARIO = "Domiciliario"
    CLIENTE = "Cliente"


class ClientePerfilCrear(BaseModel):
    tipoCliente: Literal["Nuevo", "Frecuente", "Ocasional"] = "Nuevo"
    direccion: str = Field(min_length=1, max_length=150)


class PanaderoPerfilCrear(BaseModel):
    estadoActividad: Literal["En Turno", "Descanso", "Inactivo"] = "Inactivo"


class DomiciliarioPerfilCrear(BaseModel):
    estadoDisponibilidad: Literal["Libre", "Ocupado", "Inactivo"] = "Libre"


class UsuarioCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=45)
    apellido: str = Field(min_length=2, max_length=45)
    correo: EmailStr
    contrasena: str = Field(min_length=12, max_length=128)
    telefono: str = Field(
        min_length=10,
        max_length=13,
        pattern=r"^(?:\+?57)?3\d{9}$",
    )
    direccion: str | None = Field(default=None, min_length=1, max_length=150)
    rol: UserRole = UserRole.CLIENTE
    perfil_cliente: ClientePerfilCrear | None = None
    perfil_panadero: PanaderoPerfilCrear | None = None
    perfil_domiciliario: DomiciliarioPerfilCrear | None = None

    @model_validator(mode="after")
    def validar_perfiles_por_rol(self):
        perfiles = (
            self.perfil_cliente,
            self.perfil_panadero,
            self.perfil_domiciliario,
        )

        if self.rol == UserRole.SUPERADMIN:
            raise ValueError(
                "El Superadmin debe crearse mediante el flujo de bootstrap."
            )

        if self.rol == UserRole.CLIENTE:
            if self.perfil_cliente is None and self.direccion is None:
                raise ValueError("El cliente debe tener una dirección.")
            if self.perfil_panadero is not None or self.perfil_domiciliario is not None:
                raise ValueError("Un cliente no puede tener perfil de empleado.")
        elif self.rol == UserRole.PANADERO:
            if self.perfil_panadero is None:
                raise ValueError("El Panadero debe tener un perfil de panadero.")
            if self.perfil_cliente is not None or self.perfil_domiciliario is not None:
                raise ValueError("El Panadero solo puede tener perfil de panadero.")
        elif self.rol == UserRole.DOMICILIARIO:
            if self.perfil_domiciliario is None:
                raise ValueError(
                    "El Domiciliario debe tener un perfil de domiciliario."
                )
            if self.perfil_cliente is not None or self.perfil_panadero is not None:
                raise ValueError(
                    "El Domiciliario solo puede tener perfil de domiciliario."
                )
        elif any(perfiles):
            raise ValueError(
                "El Administrador no puede tener perfil de cliente ni de empleado."
            )

        return self



class UsuarioActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=45)
    apellido: str | None = Field(default=None, min_length=2, max_length=45)
    correo: EmailStr | None = None
    telefono: str | None = Field(
        default=None,
        min_length=10,
        max_length=13,
        pattern=r"^(?:\+?57)?3\d{9}$",
    )
    direccion: str | None = Field(
        default=None, min_length=1, max_length=150
    )
    rol: UserRole | None = None


class UsuarioEstadoActualizar(BaseModel):
    estado: Literal["Activo", "Inactivo"]


class UsuarioRespuesta(BaseModel):
    idUsuario: int
    nombre: str
    apellido: str
    correo: EmailStr
    telefono: str
    direccion: str | None = None
    estado: str
    Rol_idRol: int

    model_config = ConfigDict(from_attributes=True)


UserResponse = UsuarioRespuesta
UserCreate = UsuarioCrear
UserUpdate = UsuarioActualizar

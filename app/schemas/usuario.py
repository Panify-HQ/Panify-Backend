from pydantic import BaseModel, EmailStr, ConfigDict, Field


class UsuarioCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=45)
    apellido: str = Field(min_length=2, max_length=45)
    correo: EmailStr
    contrasena: str = Field(min_length=8, max_length=128)
    telefono: str = Field(pattern=r"^(?:\+57)?[0-9]{10}$")
    direccion: str = Field(min_length=1, max_length=150)


class UsuarioRespuesta(BaseModel):
    idUsuario: int
    nombre: str
    apellido: str
    correo: EmailStr
    telefono: str
    estado: str
    Rol_idRol: int

    model_config = ConfigDict(from_attributes=True)

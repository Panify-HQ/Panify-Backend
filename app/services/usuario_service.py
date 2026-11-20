from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.core.security import hash_password


def crear_usuario(
    db: Session,
    nombre: str,
    apellido: str,
    correo: str,
    contrasena: str,
    telefono: str,
    rol_id: int,
    direccion: str | None = None,
    estado: str = "Activo",
    cliente_id: int | None = None,
    panadero_id: int | None = None,
    domiciliario_id: int | None = None,
) -> Usuario:
    """Registra un usuario nuevo y protege su contraseña."""

    try:
        # Comprobar si el correo ya está registrado
        usuario_existente = db.scalar(select(Usuario).where(Usuario.correo == correo))

        if usuario_existente:
            raise ValueError("El correo electrónico ya está registrado.")

        # Comprobar si el rol existe
        rol_existente = db.get(Rol, rol_id)

        if rol_existente is None:
            raise ValueError("El rol seleccionado no existe.")

        # Proteger la contraseña
        contrasena_hash = hash_password(contrasena)

        # Crear el nuevo usuario
        nuevo_usuario = Usuario(
            nombre=nombre,
            apellido=apellido,
            correo=correo,
            contrasena=contrasena_hash,
            telefono=telefono,
            estado=estado,
            Rol_idRol=rol_id,
            cliente_idCliente=None if direccion is not None else cliente_id,
            panadero_idPanadero=panadero_id,
            domiciliario_idDomiciliario=domiciliario_id,
        )

        db.add(nuevo_usuario)
        db.flush()

        if direccion is not None:
            cliente = Cliente(
                idCliente=nuevo_usuario.idUsuario,
                tipoCliente="Nuevo",
                direccion=direccion,
            )
            db.add(cliente)
            db.flush()
            nuevo_usuario.cliente_idCliente = cliente.idCliente

        db.commit()
        db.refresh(nuevo_usuario)

        return nuevo_usuario

    except ValueError:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

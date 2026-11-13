
from getpass import getpass

from email_validator import validate_email, EmailNotValidError
from sqlalchemy import select

from app.core.security import hash_password
from app.infrastructure.database.session import SessionLocal
from app.models.usuario import Usuario
from app.models.rol import Rol


def solicitar_datos() -> dict:
    """Solicita y valida los datos del Superadmin."""

    print("\n=== CREACIÓN DEL SUPERADMIN DE PANIFY ===")

    nombre = input("Nombre: ").strip()
    while not nombre:
        print("El nombre es obligatorio.")
        nombre = input("Nombre: ").strip()

    apellido = input("Apellido: ").strip()
    while not apellido:
        print("El apellido es obligatorio.")
        apellido = input("Apellido: ").strip()

    while True:
        correo = input("Correo electrónico: ").strip().lower()
        try:
            validate_email(correo, check_deliverability=False)
            break
        except EmailNotValidError:
            print("Ingresa un correo electrónico válido.")

    telefono = input("Teléfono: ").strip()
    while len(telefono) < 7 or len(telefono) > 15:
        print("El teléfono debe tener entre 7 y 15 caracteres.")
        telefono = input("Teléfono: ").strip()

    while True:
        contrasena = getpass("Contraseña (mínimo 12 caracteres): ")

        if len(contrasena) < 12:
            print("La contraseña debe tener al menos 12 caracteres.")
            continue

        confirmacion = getpass("Confirma la contraseña: ")

        if contrasena != confirmacion:
            print("Las contraseñas no coinciden.")
            continue

        break

    return {
        "nombre": nombre,
        "apellido": apellido,
        "correo": correo,
        "telefono": telefono,
        "contrasena": contrasena,
    }


def crear_superadmin():
    db = SessionLocal()

    try:
        # Comprobar que no exista ya un Superadmin
        superadmin_existente = db.scalar(
            select(Usuario)
            .join(Usuario.rol)
            .where(Rol.nombre == "Superadmin")
        )

        if superadmin_existente:
            print("Ya existe un Superadmin. No se creará otro.")
            return

        # Buscar el rol Superadmin
        rol_superadmin = db.scalar(
            select(Rol).where(Rol.nombre == "Superadmin")
        )

        if not rol_superadmin:
            print("No existe el rol Superadmin en la base de datos.")
            print("Verifica los registros de la tabla rol.")
            return

        datos = solicitar_datos()

        # Comprobar que el correo no esté registrado
        usuario_existente = db.scalar(
            select(Usuario).where(
                Usuario.correo == datos["correo"]
            )
        )

        if usuario_existente:
            print("Ese correo ya está registrado.")
            return

        # Proteger la contraseña
        contrasena_hash = hash_password(datos["contrasena"])

        nuevo_superadmin = Usuario(
            nombre=datos["nombre"],
            apellido=datos["apellido"],
            correo=datos["correo"],
            contrasena=contrasena_hash,
            telefono=datos["telefono"],
            estado="Activo",
            Rol_idRol=rol_superadmin.id,
        )

        db.add(nuevo_superadmin)
        db.commit()
        db.refresh(nuevo_superadmin)

        print("\nSuperadmin creado correctamente.")
        print(f"ID: {nuevo_superadmin.idUsuario}")
        print(f"Correo: {nuevo_superadmin.correo}")
        print("Guarda tus credenciales en un lugar seguro.")

    except Exception as error:
        db.rollback()
        print(f"\nError al crear el Superadmin: {error}")

    finally:
        db.close()


if __name__ == "__main__":
    crear_superadmin()

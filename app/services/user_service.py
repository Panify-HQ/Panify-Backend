from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.cliente import Cliente
from app.models.domiciliario import Domiciliario
from app.models.panaderos import Panadero
from app.models.roles import Rol
from app.models.usuario import Usuario
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserRole, UserUpdate


class UserServiceError(Exception):
    pass


class UserNotFoundError(UserServiceError):
    pass


class UserAlreadyExistsError(UserServiceError):
    pass


class UserRoleNotFoundError(UserServiceError):
    pass


class UserService:
    @staticmethod
    def create_user(db: Session, data: UserCreate) -> Usuario:
        email = str(data.correo).strip().lower()

        if UserRepository.get_by_email(db, email) is not None:
            raise UserAlreadyExistsError(
                "Ya existe un usuario registrado con ese correo."
            )

        role = db.scalar(select(Rol).where(Rol.nombre == data.rol.value))
        if role is None:
            raise UserRoleNotFoundError(f"El rol {data.rol.value} no está configurado.")

        direccion = data.direccion
        tipo_cliente = "Nuevo"
        if data.perfil_cliente is not None:
            direccion = data.perfil_cliente.direccion
            tipo_cliente = data.perfil_cliente.tipoCliente

        try:
            user = Usuario(
                nombre=data.nombre.strip(),
                apellido=data.apellido.strip(),
                correo=email,
                contrasena=hash_password(data.contrasena),
                telefono=data.telefono,
                estado="Activo",
                Rol_idRol=role.idRol,
            )
            db.add(user)
            db.flush()

            if data.rol == UserRole.CLIENTE:
                cliente = Cliente(
                    idCliente=user.idUsuario,
                    tipoCliente=tipo_cliente,
                    direccion=direccion,
                )
                db.add(cliente)
                db.flush()
                user.cliente_idCliente = cliente.idCliente
            elif data.rol == UserRole.PANADERO:
                panadero = Panadero(
                    idPanadero=user.idUsuario,
                    estadoActividad=(
                        data.perfil_panadero.estadoActividad
                        if data.perfil_panadero is not None
                        else "Inactivo"
                    ),
                )
                db.add(panadero)
                db.flush()
                user.panadero_idPanadero = panadero.idPanadero
            elif data.rol == UserRole.DOMICILIARIO:
                domiciliario = Domiciliario(
                    idDomiciliario=user.idUsuario,
                    estadoDisponibilidad=(
                        data.perfil_domiciliario.estadoDisponibilidad
                        if data.perfil_domiciliario is not None
                        else "Libre"
                    ),
                )
                db.add(domiciliario)
                db.flush()
                user.domiciliario_idDomiciliario = domiciliario.idDomiciliario

            db.commit()
            db.refresh(user)
            return user
        except IntegrityError as exc:
            db.rollback()
            raise UserAlreadyExistsError(
                "No fue posible crear el usuario. "
                "Verifica que el correo no esté duplicado."
            ) from exc
        except ValueError as exc:
            db.rollback()
            if str(exc) == "El correo electrónico ya está registrado.":
                raise UserAlreadyExistsError(str(exc)) from exc
            raise UserServiceError(str(exc)) from exc
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_user(db: Session, user_id: int) -> Usuario:
        user = UserRepository.get_by_id(db, user_id)
        if user is None:
            raise UserNotFoundError("Usuario no encontrado.")
        return user

    @staticmethod
    def list_users(
        db: Session,
        role: UserRole | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Usuario]:
        return UserRepository.list_users(
            db=db,
            role=role.value if role is not None else None,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        data: UserUpdate,
    ) -> Usuario:
        user = UserService.get_user(db, user_id)

        if user.rol.nombre == UserRole.SUPERADMIN.value:
            raise UserServiceError(
                "No se puede modificar el Superadmin desde este módulo."
            )

        changes = data.model_dump(exclude_unset=True)
        if "correo" in changes:
            if changes["correo"] is None:
                raise UserServiceError("El correo no puede ser nulo.")

            email = str(changes["correo"]).strip().lower()
            existing = UserRepository.get_by_email(db, email)
            if existing is not None and existing.idUsuario != user.idUsuario:
                raise UserAlreadyExistsError(
                    "Ese correo electrónico ya está registrado."
                )
            changes["correo"] = email

        actualiza_direccion = "direccion" in changes
        direccion = changes.pop("direccion", None)
        cliente = None
        if actualiza_direccion:
            if direccion is None or not direccion.strip():
                raise UserServiceError("La dirección no puede ser nula ni vacía.")
            if user.cliente_idCliente is None:
                raise UserServiceError(
                    "Solo se puede actualizar la dirección de un cliente."
                )
            cliente = db.get(Cliente, user.cliente_idCliente)
            if cliente is None:
                raise UserServiceError("No se encontró el perfil del cliente.")

        for field, value in changes.items():
            if value is None:
                raise UserServiceError(f"{field} no puede ser nulo.")
            if isinstance(value, str):
                value = value.strip()
            setattr(user, field, value)

        if cliente is not None:
            cliente.direccion = direccion.strip()

        try:
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError as exc:
            db.rollback()
            raise UserAlreadyExistsError(
                "No fue posible actualizar el usuario. "
                "Verifica que el correo no esté duplicado."
            ) from exc
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def change_status(
        db: Session,
        user_id: int,
        is_active: bool,
        current_user_id: int,
    ) -> Usuario:
        user = UserService.get_user(db, user_id)

        if user.rol.nombre == UserRole.SUPERADMIN.value:
            raise UserServiceError("No se puede cambiar el estado del Superadmin.")

        if user.idUsuario == current_user_id and not is_active:
            raise UserServiceError("No puedes desactivar tu propia cuenta.")

        user.estado = "Activo" if is_active else "Inactivo"

        try:
            db.commit()
            db.refresh(user)
            return user
        except Exception:
            db.rollback()
            raise

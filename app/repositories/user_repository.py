from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.roles import Rol
from app.models.usuario import Usuario


class UserRepository:

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Usuario | None:
        return db.get(Usuario, user_id)

    @staticmethod
    def get_by_email(db: Session, email: str) -> Usuario | None:
        normalized_email = email.strip().lower()
        return db.scalar(select(Usuario).where(Usuario.correo == normalized_email))

    @staticmethod
    def list_users(
        db: Session,
        role: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Usuario]:
        query = select(Usuario)

        if role is not None:
            query = query.join(Usuario.rol).where(Rol.nombre == role)

        if is_active is not None:
            estado = "Activo" if is_active else "Inactivo"
            query = query.where(Usuario.estado == estado)

        query = query.order_by(Usuario.idUsuario.desc()).offset(skip).limit(limit)

        return list(db.scalars(query).all())

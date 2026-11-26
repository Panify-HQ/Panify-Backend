import hashlib
import hmac
import logging
import secrets

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password

from app.models.usuario import Usuario
from app.models.codigo_restablecimiento import CodigoRestablecimiento

from app.services.email_service import enviar_correo


logger = logging.getLogger(__name__)

TIEMPO_VIGENCIA_MINUTOS = 5
MAX_INTENTOS = 3
ESPERA_ENTRE_SOLICITUDES_SEGUNDOS = 60


def obtener_fecha_actual():
    """
    Devuelve la fecha UTC sin zona horaria,
    compatible con las columnas DateTime de MySQL.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generar_hash_codigo(usuario_id: int, codigo: str) -> str:
    """
    Protege el código utilizando HMAC-SHA256.
    """

    secreto = settings.JWT_SECRET_KEY.encode("utf-8")

    contenido = f"panify-reset:{usuario_id}:{codigo}".encode("utf-8")

    return hmac.new(
        secreto,
        contenido,
        hashlib.sha256
    ).hexdigest()


def solicitar_codigo(db: Session, correo: str) -> str:
    """
    Busca al usuario, genera un código y lo envía por Gmail.
    """

    correo = str(correo).strip().lower()

    # Buscar usuario por correo
    usuario = db.scalar(
        select(Usuario).where(
            func.lower(Usuario.correo) == correo
        )
    )

    # Comprobar si el correo está registrado
    if usuario is None:
        return "no_registrado"

    ahora = obtener_fecha_actual()

    # Obtener la última solicitud
    ultimo_codigo = db.scalar(
        select(CodigoRestablecimiento)
        .where(
            CodigoRestablecimiento.usuario_idUsuario == usuario.idUsuario
        )
        .order_by(CodigoRestablecimiento.creado_en.desc())
        .limit(1)
    )

    # Evitar solicitudes repetidas
    if (
        ultimo_codigo is not None
        and ultimo_codigo.creado_en >
        ahora - timedelta(seconds=ESPERA_ENTRE_SOLICITUDES_SEGUNDOS)
    ):
        return "espera"

    # Invalidar códigos anteriores
    db.execute(
        update(CodigoRestablecimiento)
        .where(
            CodigoRestablecimiento.usuario_idUsuario == usuario.idUsuario,
            CodigoRestablecimiento.usado.is_(False)
        )
        .values(usado=True)
    )

    # Generar seis dígitos aleatorios
    codigo = f"{secrets.randbelow(1_000_000):06d}"

    # Crear registro
    registro = CodigoRestablecimiento(
        usuario_idUsuario=usuario.idUsuario,
        codigo_hash=generar_hash_codigo(
            usuario.idUsuario,
            codigo
        ),
        creado_en=ahora,
        vence_en=ahora + timedelta(
            minutes=TIEMPO_VIGENCIA_MINUTOS
        ),
        intentos=0,
        usado=False
    )

    db.add(registro)
    db.commit()
    db.refresh(registro)

    # Preparar correo de texto plano
    mensaje_texto = f"""
Hola {usuario.nombre}.

Recibimos una solicitud para restablecer tu contraseña de Panify.

Tu código de verificación es:

{codigo}

Este código tiene una vigencia de 5 minutos.

Dispones de 3 intentos para introducirlo correctamente.

Si no solicitaste este cambio, puedes ignorar este mensaje.

Equipo Panify.
"""

    # Enviar correo mediante Gmail SMTP
    try:
        enviar_correo(
            destinatario=usuario.correo,
            asunto="Código para restablecer tu contraseña - Panify",
            mensaje_texto=mensaje_texto
        )

    except Exception:
        logger.exception(
            "No fue posible enviar el código de recuperación."
        )

        registro.usado = True
        db.commit()

        return "error_envio"

    return "enviado"


def restablecer_contrasena(
    db: Session,
    correo: str,
    codigo: str,
    nueva_contrasena: str
) -> None:
    """
    Valida el código y cambia la contraseña del usuario.
    """

    correo = str(correo).strip().lower()

    usuario = db.scalar(
        select(Usuario).where(
            func.lower(Usuario.correo) == correo
        )
    )

    if usuario is None:
        raise ValueError(
            "El código es incorrecto o ha vencido."
        )

    # Obtener el código pendiente más reciente
    registro = db.scalar(
        select(CodigoRestablecimiento)
        .where(
            CodigoRestablecimiento.usuario_idUsuario == usuario.idUsuario,
            CodigoRestablecimiento.usado.is_(False)
        )
        .order_by(CodigoRestablecimiento.creado_en.desc())
        .limit(1)
        .with_for_update()
    )

    if registro is None:
        raise ValueError(
            "El código es incorrecto o ha vencido."
        )

    ahora = obtener_fecha_actual()

    # Comprobar vencimiento
    if ahora >= registro.vence_en:
        registro.usado = True
        db.commit()

        raise ValueError(
            "El código ha vencido. Solicita uno nuevo."
        )

    # Comprobar límite de intentos
    if registro.intentos >= MAX_INTENTOS:
        registro.usado = True
        db.commit()

        raise ValueError(
            "Has superado el límite de intentos."
        )

    # Calcular hash recibido
    hash_recibido = generar_hash_codigo(
        usuario.idUsuario,
        codigo
    )

    # Comparar códigos
    if not hmac.compare_digest(
        hash_recibido,
        registro.codigo_hash
    ):

        registro.intentos += 1

        if registro.intentos >= MAX_INTENTOS:
            registro.usado = True

        db.commit()

        raise ValueError(
            "El código es incorrecto o ha vencido."
        )

    # Actualizar contraseña
    usuario.contrasena = hash_password(nueva_contrasena)

    # Marcar código como utilizado
    registro.usado = True

    # Invalidar otros códigos pendientes
    db.execute(
        update(CodigoRestablecimiento)
        .where(
            CodigoRestablecimiento.usuario_idUsuario == usuario.idUsuario,
            CodigoRestablecimiento.idCodigo != registro.idCodigo,
            CodigoRestablecimiento.usado.is_(False)
        )
        .values(usado=True)
    )

    db.commit()
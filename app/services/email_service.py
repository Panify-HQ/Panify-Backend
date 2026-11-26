import smtplib
import ssl

from email.message import EmailMessage
from smtplib import SMTPAuthenticationError, SMTPException

from app.core.config import settings


def enviar_correo(
    destinatario: str,
    asunto: str,
    mensaje_texto: str,
    mensaje_html: str | None = None
) -> None:
    """
    Envía un correo utilizando Gmail SMTP.
    """

    # Obtener credenciales
    correo_emisor = settings.SMTP_USER
    contrasena = (settings.SMTP_PASSWORD or "").replace(" ", "")

    if not correo_emisor or not contrasena:
        raise RuntimeError(
            "Falta configurar SMTP_USER o SMTP_PASSWORD en el .env"
        )

    # Construir mensaje
    correo = EmailMessage()

    correo["Subject"] = asunto
    correo["From"] = (
        f"{settings.SMTP_FROM_NAME} <{correo_emisor}>"
    )
    correo["To"] = destinatario

    # Contenido de texto
    correo.set_content(mensaje_texto)

    # Contenido HTML opcional
    if mensaje_html:
        correo.add_alternative(
            mensaje_html,
            subtype="html"
        )

    try:
        contexto = ssl.create_default_context()

        # Conexión con Gmail
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=20
        ) as servidor:

            servidor.ehlo()

            servidor.starttls(context=contexto)

            servidor.ehlo()

            servidor.login(
                correo_emisor,
                contrasena
            )

            servidor.send_message(correo)

    except SMTPAuthenticationError as error:
        raise RuntimeError(
            "Gmail rechazó las credenciales. "
            "Verifica tu contraseña de aplicación."
        ) from error

    except (SMTPException, OSError) as error:
        raise RuntimeError(
            "No fue posible enviar el correo. "
            "Verifica la conexión y la configuración SMTP."
        ) from error
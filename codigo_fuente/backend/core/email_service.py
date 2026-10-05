"""
Envío de correo saliente por SMTP.

Lo usa el flujo «Olvidé mi contraseña» para enviar un código de un solo uso al
correo registrado en el perfil. Usa SMTP estándar con una contraseña de
aplicación de Gmail, sin OAuth ni dependencias adicionales. Si faltan
SMTP_USER o SMTP_APP_PASSWORD en el .env, enviar_correo() devuelve False sin
lanzar excepción: el backend sigue funcionando y el fallo queda en el log.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from config import SMTP_APP_PASSWORD, SMTP_FROM_NAME, SMTP_HOST, SMTP_PORT, SMTP_USER

logger = logging.getLogger("EmailService")


def correo_configurado() -> bool:
    """Indica si hay credenciales SMTP cargadas.

    Permite dar un mensaje claro en lugar de informar que el correo salió
    cuando el servidor SMTP no está configurado.
    """
    return bool(SMTP_USER and SMTP_APP_PASSWORD)


def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> bool:
    """Envía un correo de texto plano en UTF-8 mediante SMTP con STARTTLS.

    Returns:
        True si el servidor aceptó el mensaje; False si falta configuración,
        destinatario o si ocurrió un error de envío (que se registra en el log).
    """
    if not correo_configurado():
        logger.warning(
            "[EMAIL] SMTP_USER/SMTP_APP_PASSWORD no configurados en backend/.env "
            "— correo NO enviado (asunto: %s).", asunto,
        )
        return False
    if not destinatario:
        return False

    mensaje = MIMEText(cuerpo, "plain", "utf-8")
    mensaje["Subject"] = asunto
    mensaje["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
    mensaje["To"] = destinatario

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_USER, [destinatario], mensaje.as_string())
        return True
    except Exception as exc:
        logger.error("[EMAIL] Error enviando correo a %s: %s", destinatario, exc)
        return False

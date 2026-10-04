"""
core/email_service.py — Envío de correo saliente (SMTP) de VicMar Data AI.

Hoy el único uso es "Olvidé mi contraseña" (Mi Perfil, Fase 5, 28/08/2026):
un código de un solo uso enviado al correo que el usuario registró en su
perfil. Usa SMTP estándar con una contraseña de aplicación de Gmail — sin
OAuth ni librerías nuevas — porque es lo que el usuario ya tiene disponible
(una cuenta Gmail propia).

Si SMTP_USER o SMTP_APP_PASSWORD no están configurados en el .env,
enviar_correo() devuelve False sin lanzar excepción: el backend sigue
funcionando igual, solo que sin poder enviar correos (queda registrado en el
log para que se note en desarrollo, sin tumbar la petición que lo dispara).
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from config import SMTP_APP_PASSWORD, SMTP_FROM_NAME, SMTP_HOST, SMTP_PORT, SMTP_USER

logger = logging.getLogger("EmailService")


def correo_configurado() -> bool:
    """¿Hay credenciales SMTP cargadas? Se usa para dar un mensaje claro en
    vez de fingir que el correo salió cuando en realidad nadie lo configuró."""
    return bool(SMTP_USER and SMTP_APP_PASSWORD)


def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> bool:
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

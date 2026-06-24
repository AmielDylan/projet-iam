"""SMTP email helpers."""
from __future__ import annotations

from email.message import EmailMessage
import smtplib

from flask import current_app


class EmailDeliveryError(RuntimeError):
    """Raised when an email could not be sent."""


class EmailService:
    """Send transactional email through SMTP environment configuration."""

    @staticmethod
    def send(to_address: str, subject: str, body: str) -> None:
        config = current_app.config["APP_CONFIG"]
        host = getattr(config, "SMTP_HOST", "")
        from_address = getattr(config, "SMTP_FROM", "") or getattr(config, "SMTP_USER", "")
        if not host or not from_address:
            raise EmailDeliveryError("Configuration SMTP manquante.")

        message = EmailMessage()
        message["From"] = from_address
        message["To"] = to_address
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(host, int(getattr(config, "SMTP_PORT", 587)), timeout=15) as smtp:
                if getattr(config, "SMTP_TLS", True):
                    smtp.starttls()
                user = getattr(config, "SMTP_USER", "")
                password = getattr(config, "SMTP_PASSWORD", "")
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(message)
        except Exception as exc:
            raise EmailDeliveryError("Email non envoyé.") from exc

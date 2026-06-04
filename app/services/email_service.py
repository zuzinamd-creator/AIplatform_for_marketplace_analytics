import asyncio
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.observability import get_logger

logger = get_logger("email")


class EmailDeliveryError(RuntimeError):
    pass


def _smtp_configured() -> bool:
    return bool(settings.smtp_host.strip() and settings.smtp_from.strip())


def smtp_configured() -> bool:
    return _smtp_configured()


def _send_smtp_sync(*, to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as client:
            if settings.smtp_user:
                client.login(settings.smtp_user, settings.smtp_password)
            client.send_message(msg)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as client:
        if settings.smtp_use_tls:
            client.starttls()
        if settings.smtp_user:
            client.login(settings.smtp_user, settings.smtp_password)
        client.send_message(msg)


async def send_email(*, to: str, subject: str, body: str) -> None:
    if not _smtp_configured():
        raise EmailDeliveryError("SMTP is not configured (set SMTP_HOST and SMTP_FROM in .env)")
    try:
        await asyncio.to_thread(
            _send_smtp_sync,
            to=to,
            subject=subject,
            body=body,
        )
    except Exception as exc:
        logger.exception("email_send_failed", extra={"to": to, "subject": subject})
        raise EmailDeliveryError("Failed to send email") from exc

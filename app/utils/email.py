import logging
from urllib.parse import urlencode

import httpx
from app.config import settings
from app.utils import verification_email

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    pass


def build_verification_url(token: str) -> str:
    return f"{settings.frontend_verify_url}?{urlencode({'token': token})}"


async def send_verification_email(email: str, token: str) -> None:
    provider = settings.email_provider
    verification_url = build_verification_url(token)
    recipient = (
        settings.email_test_recipient
        if settings.app_env == "development" and settings.email_test_recipient
        else email
    )

    if provider in {"resend", "render"}:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {settings.resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json = {
                        "from": settings.email_from,
                        "to": [recipient],
                        "subject": "Verify your MoneyHana email",
                        "html": verification_email(verification_url),
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            logger.error(
                "Email provider rejected verification request: status=%s detail=%s",
                exc.response.status_code,
                detail,
            )
            raise EmailDeliveryError("Failed to send verification email") from exc
        except httpx.HTTPError as exc:
            logger.exception("Failed to reach email provider")
            raise EmailDeliveryError("Failed to send verification email") from exc
        return

    # Default free scaffold mode: log verification link locally.
    logger.debug("Email verification link for %s: %s", email, verification_url)

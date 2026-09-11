from abc import ABC, abstractmethod
import uuid
import logging

logger = logging.getLogger(__name__)


class WhatsAppService(ABC):
    """
    Abstraction over whichever WhatsApp provider we're using.
    Swap MockWhatsAppService for MetaWhatsAppService / TwilioWhatsAppService
    later without touching the scheduler, Celery tasks, or models.
    """

    @abstractmethod
    def send(self, to: str, template_name: str, params: dict) -> dict:
        """
        Sends a WhatsApp message.

        Returns:
            {"success": bool, "provider_message_id": str | None, "error": str | None}
        """
        ...


class MockWhatsAppService(WhatsAppService):
    """
    Does not send anything real. Logs what WOULD have been sent and returns
    a fake provider message id, so the rest of the pipeline (status updates,
    retries, dedup) can be built and tested end-to-end before real WhatsApp
    Business API credentials exist.
    """

    def send(self, to: str, template_name: str, params: dict) -> dict:
        fake_id = f"mock_{uuid.uuid4().hex[:12]}"
        logger.info(
            "\n" + "=" * 50 +
            f"\n[MOCK WHATSAPP]\n"
            f"To: {to}\n"
            f"Template: {template_name}\n"
            f"Params: {params}\n"
            f"Provider ID: {fake_id}\n" +
            "=" * 50
        )
        return {"success": True, "provider_message_id": fake_id, "error": None}


def get_whatsapp_service() -> WhatsAppService:
    """
    Single place to decide which provider is active.

    # TODO: once real credentials exist, do something like:
    #
    # from app.core.config import settings
    #
    # if settings.WHATSAPP_PROVIDER == "meta":
    #     return MetaWhatsAppService(
    #         phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
    #         access_token=settings.WHATSAPP_ACCESS_TOKEN,
    #     )
    # if settings.WHATSAPP_PROVIDER == "twilio":
    #     return TwilioWhatsAppService(...)
    """
    return MockWhatsAppService()
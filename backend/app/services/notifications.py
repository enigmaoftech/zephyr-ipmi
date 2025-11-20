"""Notification dispatchers for external channels."""
from __future__ import annotations

import abc
import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.security import SecretManager

logger = logging.getLogger(__name__)


class NotificationError(RuntimeError):
    """Raised when a notification attempt fails."""


@dataclass(slots=True)
class NotificationMessage:
    subject: str
    body: str
    metadata: dict[str, str] | None = None


class NotificationProvider(Protocol):
    async def send(self, message: NotificationMessage) -> None:
        ...


class WebhookProvider(abc.ABC):
    """Base class for webhook-style integrations with encrypted endpoints."""

    def __init__(self, encrypted_endpoint: str, secret_manager: SecretManager) -> None:
        self._secret_manager = secret_manager
        self._endpoint = self._secret_manager.decrypt(encrypted_endpoint)

    async def _post_json(self, payload: dict) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(self._endpoint, json=payload)
        if response.status_code >= 400:
            raise NotificationError(f"Webhook response {response.status_code}: {response.text}")


class SlackProvider(WebhookProvider):
    async def send(self, message: NotificationMessage) -> None:  # type: ignore[override]
        payload = {
            "text": f"*{message.subject}*\n{message.body}",
        }
        await self._post_json(payload)


class TeamsProvider(WebhookProvider):
    async def send(self, message: NotificationMessage) -> None:  # type: ignore[override]
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.4",
                        "body": [
                            {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": message.subject},
                            {"type": "TextBlock", "text": message.body, "wrap": True},
                        ],
                    },
                }
            ],
        }
        await self._post_json(payload)


class DiscordProvider(WebhookProvider):
    async def send(self, message: NotificationMessage) -> None:  # type: ignore[override]
        payload = {"content": f"**{message.subject}**\n{message.body}"}
        await self._post_json(payload)


class TelegramProvider(NotificationProvider):
    def __init__(self, encrypted_bot_token: str, chat_id: str, secret_manager: SecretManager) -> None:
        self._secret_manager = secret_manager
        self._bot_token = self._secret_manager.decrypt(encrypted_bot_token)
        self._chat_id = chat_id

    async def send(self, message: NotificationMessage) -> None:
        payload = {
            "chat_id": self._chat_id,
            "text": f"{message.subject}\n{message.body}",
        }
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
        if response.status_code >= 400:
            raise NotificationError(f"Telegram response {response.status_code}: {response.text}")


async def notify(provider: NotificationProvider, message: NotificationMessage) -> None:
    try:
        await provider.send(message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to deliver notification: %s", exc)
        raise NotificationError(str(exc)) from exc

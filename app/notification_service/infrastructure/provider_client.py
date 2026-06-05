from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from notification_service.domain.exceptions import ProviderResponseError, ProviderRetryableError
from notification_service.domain.models import NotificationRequest
from notification_service.infrastructure.settings import Settings

logger = logging.getLogger(__name__)


class ProviderClient:
    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def extract(self, user_input: str) -> str:
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a notification extraction engine. "
                        "Extract the destination, message and channel from the user input. "
                        "Return a single JSON object with keys to, message and type. "
                        "Valid type values are email or sms. "
                        "Do not include markdown or explanations."
                    ),
                },
                {"role": "user", "content": user_input},
            ]
        }
        response_payload = await self._post_with_retry("/v1/ai/extract", json=payload)
        try:
            return response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderResponseError("The AI provider returned an invalid response schema.") from exc

    async def notify(self, notification: NotificationRequest) -> dict[str, Any]:
        payload = {
            "to": notification.to,
            "message": notification.message,
            "type": notification.type.value,
        }
        return await self._post_with_retry("/v1/notify", json=payload)

    async def _post_with_retry(self, path: str, *, json: dict[str, Any]) -> dict[str, Any]:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._settings.provider_max_attempts),
            wait=wait_exponential(multiplier=0.2, min=0.2, max=1.0),
            retry=retry_if_exception_type((ProviderRetryableError, httpx.TransportError)),
            reraise=True,
        ):
            with attempt:
                try:
                    response = await self._client.post(path, json=json)
                except httpx.TransportError as exc:
                    logger.warning("Provider network error on %s: %s", path, exc)
                    raise

                if response.status_code in {429, 500, 502, 503, 504}:
                    raise ProviderRetryableError(self._extract_error_message(response))
                if response.status_code >= 400:
                    raise ProviderResponseError(self._extract_error_message(response))

                try:
                    return response.json()
                except ValueError as exc:
                    raise ProviderResponseError("Provider returned a non-JSON response.") from exc

        raise ProviderResponseError("Unexpected provider retry exhaustion.")

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text or f"Provider request failed with status {response.status_code}."

        if isinstance(payload, dict):
            detail = payload.get("detail") or payload.get("error")
            if detail:
                return str(detail)
        return f"Provider request failed with status {response.status_code}."

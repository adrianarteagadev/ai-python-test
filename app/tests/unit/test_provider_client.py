import httpx
import pytest

from notification_service.domain.exceptions import ProviderResponseError
from notification_service.domain.models import NotificationRequest, NotificationType
from notification_service.infrastructure.provider_client import ProviderClient
from notification_service.infrastructure.settings import Settings


@pytest.mark.asyncio
async def test_provider_client_retries_transient_notify_failures(settings: Settings):
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            return httpx.Response(429, json={"detail": "Rate limit exceeded"})
        return httpx.Response(200, json={"status": "delivered", "provider_id": "p-1234"})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(
        base_url=settings.provider_base_url,
        transport=transport,
        headers={"X-API-Key": settings.provider_api_key},
    )
    provider_client = ProviderClient(client, settings)

    result = await provider_client.notify(
        NotificationRequest(to="user@test.com", message="Hola", type=NotificationType.EMAIL)
    )

    await client.aclose()
    assert attempts["count"] == 3
    assert result["provider_id"] == "p-1234"


@pytest.mark.asyncio
async def test_provider_client_raises_on_non_retryable_errors(settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Invalid API Key"})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(
        base_url=settings.provider_base_url,
        transport=transport,
        headers={"X-API-Key": settings.provider_api_key},
    )
    provider_client = ProviderClient(client, settings)

    with pytest.raises(ProviderResponseError):
        await provider_client.extract("Enviar email a user@test.com diciendo hola")

    await client.aclose()

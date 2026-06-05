from __future__ import annotations

from dataclasses import dataclass

import httpx

from notification_service.application.services import RequestService
from notification_service.infrastructure.llm_sanitizer import LlmResponseSanitizer
from notification_service.infrastructure.orchestrator import ProcessingOrchestrator
from notification_service.infrastructure.provider_client import ProviderClient
from notification_service.infrastructure.repository import InMemoryRequestRepository
from notification_service.infrastructure.settings import Settings, load_settings


@dataclass
class ServiceContainer:
    repository: InMemoryRequestRepository
    provider_client: ProviderClient
    sanitizer: LlmResponseSanitizer
    orchestrator: ProcessingOrchestrator
    request_service: RequestService
    http_client: httpx.AsyncClient

    async def start(self) -> None:
        await self.orchestrator.start()

    async def stop(self) -> None:
        await self.orchestrator.stop()
        await self.http_client.aclose()


def build_container(settings: Settings | None = None) -> ServiceContainer:
    settings = settings or load_settings()
    http_client = httpx.AsyncClient(
        base_url=settings.provider_base_url,
        headers={
            "X-API-Key": settings.provider_api_key,
            "Content-Type": "application/json",
        },
        timeout=settings.provider_timeout_seconds,
        transport=settings.provider_transport,
    )
    repository = InMemoryRequestRepository()
    sanitizer = LlmResponseSanitizer()
    provider_client = ProviderClient(http_client, settings)
    orchestrator = ProcessingOrchestrator(
        repository,
        provider_client,
        sanitizer,
        worker_count=settings.worker_count,
    )
    request_service = RequestService(repository, orchestrator)
    return ServiceContainer(
        repository=repository,
        provider_client=provider_client,
        sanitizer=sanitizer,
        orchestrator=orchestrator,
        request_service=request_service,
        http_client=http_client,
    )

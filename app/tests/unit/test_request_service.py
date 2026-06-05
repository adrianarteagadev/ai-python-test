import pytest

from notification_service.application.services import ProcessTriggerOutcome, RequestService
from notification_service.domain.exceptions import RequestNotFoundError
from notification_service.domain.models import RequestStatus
from notification_service.infrastructure.repository import InMemoryRequestRepository


class StubOrchestrator:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.should_schedule = True

    async def enqueue(self, request) -> bool:
        self.calls.append(request.id)
        return self.should_schedule


@pytest.mark.asyncio
async def test_create_and_get_request():
    repository = InMemoryRequestRepository()
    service = RequestService(repository, StubOrchestrator())

    created = await service.create_request("Manda un email a test@test.com diciendo hola")
    fetched = await service.get_request(created.id)

    assert fetched.id == created.id
    assert fetched.status is RequestStatus.QUEUED


@pytest.mark.asyncio
async def test_trigger_processing_returns_enqueued():
    repository = InMemoryRequestRepository()
    orchestrator = StubOrchestrator()
    service = RequestService(repository, orchestrator)
    created = await service.create_request("Enviar email a user@test.com hola")

    result = await service.trigger_processing(created.id)

    assert result.outcome is ProcessTriggerOutcome.ENQUEUED
    assert orchestrator.calls == [created.id]


@pytest.mark.asyncio
async def test_trigger_processing_returns_in_progress_when_already_running():
    repository = InMemoryRequestRepository()
    orchestrator = StubOrchestrator()
    orchestrator.should_schedule = False
    service = RequestService(repository, orchestrator)
    created = await service.create_request("Enviar email a user@test.com hola")

    result = await service.trigger_processing(created.id)

    assert result.outcome is ProcessTriggerOutcome.IN_PROGRESS


@pytest.mark.asyncio
async def test_get_request_raises_when_missing():
    repository = InMemoryRequestRepository()
    service = RequestService(repository, StubOrchestrator())

    with pytest.raises(RequestNotFoundError):
        await service.get_request("missing-id")

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from notification_service.domain.exceptions import RequestNotFoundError
from notification_service.domain.models import RequestStatus, StoredRequest


class ProcessTriggerOutcome(str, Enum):
    ENQUEUED = "enqueued"
    IN_PROGRESS = "in_progress"
    ALREADY_SENT = "already_sent"


@dataclass(frozen=True)
class ProcessTriggerResult:
    request: StoredRequest
    outcome: ProcessTriggerOutcome


class RequestService:
    def __init__(self, repository, orchestrator) -> None:
        self._repository = repository
        self._orchestrator = orchestrator

    async def create_request(self, user_input: str) -> StoredRequest:
        return await self._repository.create(user_input)

    async def get_request(self, request_id: str) -> StoredRequest:
        request = await self._repository.get(request_id)
        if request is None:
            raise RequestNotFoundError(f"Request '{request_id}' was not found.")
        return request

    async def trigger_processing(self, request_id: str) -> ProcessTriggerResult:
        request = await self.get_request(request_id)

        if request.status is RequestStatus.SENT:
            return ProcessTriggerResult(
                request=request,
                outcome=ProcessTriggerOutcome.ALREADY_SENT,
            )

        scheduled = await self._orchestrator.enqueue(request)
        refreshed = await self.get_request(request_id)
        if scheduled:
            outcome = ProcessTriggerOutcome.ENQUEUED
        else:
            outcome = ProcessTriggerOutcome.IN_PROGRESS

        return ProcessTriggerResult(request=refreshed, outcome=outcome)

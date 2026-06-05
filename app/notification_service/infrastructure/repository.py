from __future__ import annotations

import asyncio
from dataclasses import replace
from uuid import uuid4

from notification_service.domain.models import RequestStatus, StoredRequest


class InMemoryRequestRepository:
    def __init__(self) -> None:
        self._requests: dict[str, StoredRequest] = {}
        self._lock = asyncio.Lock()

    async def create(self, user_input: str) -> StoredRequest:
        request = StoredRequest.create(str(uuid4()), user_input)
        async with self._lock:
            self._requests[request.id] = request
        return request

    async def get(self, request_id: str) -> StoredRequest | None:
        async with self._lock:
            request = self._requests.get(request_id)
            return replace(request) if request is not None else None

    async def set_status(
        self,
        request_id: str,
        status: RequestStatus,
        *,
        error: str | None = None,
    ) -> StoredRequest | None:
        async with self._lock:
            request = self._requests.get(request_id)
            if request is None:
                return None
            updated_request = request.with_status(status, error=error)
            self._requests[request_id] = updated_request
            return replace(updated_request)

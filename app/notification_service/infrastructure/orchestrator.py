from __future__ import annotations

import asyncio
import logging

from notification_service.domain.exceptions import NotificationServiceError
from notification_service.domain.models import RequestStatus, StoredRequest

logger = logging.getLogger(__name__)


class ProcessingOrchestrator:
    def __init__(self, repository, provider_client, sanitizer, *, worker_count: int = 4) -> None:
        self._repository = repository
        self._provider_client = provider_client
        self._sanitizer = sanitizer
        self._worker_count = worker_count
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._scheduled: set[str] = set()
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._workers:
            return
        self._workers = [
            asyncio.create_task(self._worker_loop(index), name=f"notification-worker-{index}")
            for index in range(self._worker_count)
        ]

    async def stop(self) -> None:
        for worker in self._workers:
            worker.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def enqueue(self, request: StoredRequest) -> bool:
        if request.status is RequestStatus.SENT:
            return False

        async with self._lock:
            current_request = await self._repository.get(request.id)
            if current_request is None:
                return False
            if current_request.status is RequestStatus.SENT:
                return False
            if current_request.status is RequestStatus.PROCESSING or request.id in self._scheduled:
                return False

            await self._repository.set_status(request.id, RequestStatus.QUEUED, error=None)
            self._scheduled.add(request.id)
            await self._queue.put(request.id)
            return True

    async def _worker_loop(self, worker_index: int) -> None:
        while True:
            request_id = await self._queue.get()
            try:
                await self._process_request(request_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Worker %s crashed while processing %s", worker_index, request_id)
                await self._repository.set_status(
                    request_id,
                    RequestStatus.FAILED,
                    error="Unexpected processing failure.",
                )
            finally:
                async with self._lock:
                    self._scheduled.discard(request_id)
                self._queue.task_done()

    async def _process_request(self, request_id: str) -> None:
        request = await self._repository.get(request_id)
        if request is None or request.status is RequestStatus.SENT:
            return

        await self._repository.set_status(request_id, RequestStatus.PROCESSING, error=None)
        try:
            raw_content = await self._provider_client.extract(request.user_input)
            extraction = self._sanitizer.parse(raw_content)
            await self._provider_client.notify(extraction.notification)
        except NotificationServiceError as exc:
            logger.warning("Request %s failed: %s", request_id, exc)
            await self._repository.set_status(
                request_id,
                RequestStatus.FAILED,
                error=str(exc),
            )
            return

        await self._repository.set_status(request_id, RequestStatus.SENT, error=None)

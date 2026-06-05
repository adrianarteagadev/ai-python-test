from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum


class RequestStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"


class NotificationType(str, Enum):
    EMAIL = "email"
    SMS = "sms"


@dataclass(frozen=True)
class NotificationRequest:
    to: str
    message: str
    type: NotificationType


@dataclass(frozen=True)
class ExtractionResult:
    raw_content: str
    notification: NotificationRequest


@dataclass(frozen=True)
class StoredRequest:
    id: str
    user_input: str
    status: RequestStatus
    created_at: datetime
    updated_at: datetime
    error: str | None = None

    @staticmethod
    def create(request_id: str, user_input: str) -> "StoredRequest":
        now = datetime.now(timezone.utc)
        return StoredRequest(
            id=request_id,
            user_input=user_input,
            status=RequestStatus.QUEUED,
            created_at=now,
            updated_at=now,
            error=None,
        )

    def with_status(
        self,
        status: RequestStatus,
        *,
        error: str | None = None,
    ) -> "StoredRequest":
        return replace(
            self,
            status=status,
            updated_at=datetime.now(timezone.utc),
            error=error,
        )

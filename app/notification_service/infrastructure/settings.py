from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class Settings:
    provider_base_url: str = "http://localhost:3001"
    provider_api_key: str = "test-dev-2026"
    provider_timeout_seconds: float = 6.0
    provider_max_attempts: int = 3
    worker_count: int = 4
    provider_transport: httpx.AsyncBaseTransport | None = None


def load_settings() -> Settings:
    return Settings(
        provider_base_url=os.getenv("PROVIDER_BASE_URL", "http://localhost:3001"),
        provider_api_key=os.getenv("PROVIDER_API_KEY", "test-dev-2026"),
        provider_timeout_seconds=float(os.getenv("PROVIDER_TIMEOUT_SECONDS", "6.0")),
        provider_max_attempts=int(os.getenv("PROVIDER_MAX_ATTEMPTS", "3")),
        worker_count=int(os.getenv("WORKER_COUNT", "4")),
    )

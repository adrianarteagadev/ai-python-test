from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from notification_service.app_factory import create_app
from notification_service.infrastructure.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        provider_base_url="http://provider.test",
        provider_api_key="test-dev-2026",
        provider_timeout_seconds=1.0,
        provider_max_attempts=3,
        worker_count=2,
    )


@pytest.fixture
def test_client_factory(settings: Settings):
    def _factory(handler) -> Iterator[TestClient]:
        app = create_app(
            Settings(
                provider_base_url=settings.provider_base_url,
                provider_api_key=settings.provider_api_key,
                provider_timeout_seconds=settings.provider_timeout_seconds,
                provider_max_attempts=settings.provider_max_attempts,
                worker_count=settings.worker_count,
                provider_transport=httpx.MockTransport(handler),
            )
        )
        return TestClient(app)

    return _factory

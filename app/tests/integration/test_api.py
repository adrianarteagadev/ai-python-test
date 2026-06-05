import time

import httpx

from notification_service.domain.models import RequestStatus


def wait_for_status(client, request_id: str, expected_status: str, timeout_seconds: float = 3.0):
    deadline = time.time() + timeout_seconds
    last_body = None
    while time.time() < deadline:
        response = client.get(f"/v1/requests/{request_id}")
        last_body = response.json()
        if response.status_code == 200 and last_body["status"] == expected_status:
            return response
        time.sleep(0.05)
    raise AssertionError(f"Status never reached '{expected_status}'. Last body: {last_body}")


def test_happy_path_processing_flow(test_client_factory):
    observed_headers = []
    observed_notify_payloads = []

    def handler(request):
        observed_headers.append(request.headers.get("X-API-Key"))
        if request.url.path == "/v1/ai/extract":
            return_json = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '```json\n{"to": "feda@test.com", "message": "hola", "type": "email"}\n```',
                        }
                    }
                ]
            }
            return httpx.Response(200, json=return_json)
        if request.url.path == "/v1/notify":
            observed_notify_payloads.append(request.content.decode())
            return httpx.Response(200, json={"status": "delivered", "provider_id": "p-1234"})
        return httpx.Response(404, json={"detail": "Not found"})

    with test_client_factory(handler) as client:
        create_response = client.post("/v1/requests", json={"user_input": "Manda un mail a feda@test.com diciendo hola"})
        assert create_response.status_code == 201
        request_id = create_response.json()["id"]

        process_response = client.post(f"/v1/requests/{request_id}/process")
        assert process_response.status_code == 202
        assert process_response.json()["id"] == request_id
        assert process_response.json()["status"] in {RequestStatus.QUEUED, RequestStatus.PROCESSING}

        final_status = wait_for_status(client, request_id, RequestStatus.SENT.value)
        assert final_status.json() == {"id": request_id, "status": "sent"}
        assert observed_headers == ["test-dev-2026", "test-dev-2026"]
        assert '"type": "email"' in observed_notify_payloads[0]


def test_processing_fails_when_extraction_is_irrecoverable(test_client_factory):
    def handler(request):
        if request.url.path == "/v1/ai/extract":
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "Lo siento, como IA no tengo permitido procesar datos de contacto personales.",
                            }
                        }
                    ]
                },
            )
        return httpx.Response(500, json={"detail": "notify should not be called"})

    with test_client_factory(handler) as client:
        request_id = client.post(
            "/v1/requests",
            json={"user_input": "Manda un mail a feda@test.com diciendo hola"},
        ).json()["id"]

        process_response = client.post(f"/v1/requests/{request_id}/process")
        assert process_response.status_code == 202

        final_status = wait_for_status(client, request_id, RequestStatus.FAILED.value)
        assert final_status.json() == {"id": request_id, "status": "failed"}


def test_processing_retries_notify_then_succeeds(test_client_factory):
    notify_attempts = {"count": 0}

    def handler(request):
        if request.url.path == "/v1/ai/extract":
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": '{"destination": "600-111-222", "text": "Cita", "method": "sms"}',
                            }
                        }
                    ]
                },
            )
        if request.url.path == "/v1/notify":
            notify_attempts["count"] += 1
            if notify_attempts["count"] < 3:
                return httpx.Response(500, json={"detail": "temporary failure"})
            return httpx.Response(200, json={"status": "delivered", "provider_id": "p-9999"})
        return httpx.Response(404, json={"detail": "Not found"})

    with test_client_factory(handler) as client:
        request_id = client.post(
            "/v1/requests",
            json={"user_input": "Avisar por SMS al 600-111-222 que la cita fue confirmada"},
        ).json()["id"]

        process_response = client.post(f"/v1/requests/{request_id}/process")
        assert process_response.status_code == 202

        final_status = wait_for_status(client, request_id, RequestStatus.SENT.value, timeout_seconds=4.0)
        assert final_status.json()["status"] == "sent"
        assert notify_attempts["count"] == 3


def test_returns_404_for_unknown_request(test_client_factory):
    def handler(request):
        raise AssertionError("Provider should not be called for missing request ids")

    with test_client_factory(handler) as client:
        response = client.get("/v1/requests/missing-id")
        assert response.status_code == 404

        process_response = client.post("/v1/requests/missing-id/process")
        assert process_response.status_code == 404


def test_rejects_invalid_create_payload(test_client_factory):
    def handler(request):
        raise AssertionError("Provider should not be called for invalid payloads")

    with test_client_factory(handler) as client:
        response = client.post("/v1/requests", json={"user_input": "   "})
        assert response.status_code == 422

import pytest

from notification_service.domain.exceptions import ExtractionParseError
from notification_service.infrastructure.llm_sanitizer import LlmResponseSanitizer


@pytest.mark.parametrize(
    ("raw_content", "expected_to", "expected_message", "expected_type"),
    [
        ('{"to": "User@Test.com", "message": "Hola", "type": "email"}', "user@test.com", "Hola", "email"),
        ('{"Recipient": "600-111-222", "body": "Cita confirmada", "channel": "sms"}', "600-111-222", "Cita confirmada", "sms"),
        ('He extraido la informacion:\n```json\n{"to": "marta@test.com", "message": "Aviso", "type": "email"}\n```', "marta@test.com", "Aviso", "email"),
        ('Output: {"destination": "699888777", "text": "Recordatorio", "method": "sms"}', "699888777", "Recordatorio", "sms"),
        ("{'to': 'feda@test.com', 'message': 'hola', 'type': 'email'}", "feda@test.com", "hola", "email"),
        ('{to: "feda@test.com", message: "hola", type: "email"}', "feda@test.com", "hola", "email"),
    ],
)
def test_parse_supported_llm_variants(raw_content, expected_to, expected_message, expected_type):
    sanitizer = LlmResponseSanitizer()

    result = sanitizer.parse(raw_content)

    assert result.notification.to == expected_to
    assert result.notification.message == expected_message
    assert result.notification.type.value == expected_type


@pytest.mark.parametrize(
    "raw_content",
    [
        '{"to": "feda@test.com", "message": "hola"}',
        '{"message": "hola", "type": "email"}',
        "Lo siento, como IA no tengo permitido procesar datos de contacto personales.",
        '{"to": "feda@test.com", "message": "hola", "type": "push"}',
        '{"to": "not-an-email", "message": "hola", "type": "email"}',
        '{"to": "600111222", "message": "", "type": "sms"}',
        '{"to": "feda@test.com", "message": "hola", "type": "email" ...',
    ],
)
def test_parse_rejects_invalid_payloads(raw_content):
    sanitizer = LlmResponseSanitizer()

    with pytest.raises(ExtractionParseError):
        sanitizer.parse(raw_content)

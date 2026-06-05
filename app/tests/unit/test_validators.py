import pytest

from notification_service.domain.exceptions import NotificationValidationError
from notification_service.domain.validators import validate_notification_payload


def test_validate_email_notification():
    notification = validate_notification_payload("User@Test.com", "Hola", "email")

    assert notification.to == "user@test.com"
    assert notification.type.value == "email"


def test_validate_sms_notification():
    notification = validate_notification_payload("600-111-222", "Hola", "sms")

    assert notification.to == "600-111-222"
    assert notification.type.value == "sms"


@pytest.mark.parametrize(
    ("to", "message", "raw_type"),
    [
        ("", "Hola", "email"),
        ("user@test.com", "", "email"),
        ("user@test.com", "Hola", "push"),
        ("not-an-email", "Hola", "email"),
        ("abc", "Hola", "sms"),
    ],
)
def test_validate_notification_payload_rejects_invalid_inputs(to, message, raw_type):
    with pytest.raises(NotificationValidationError):
        validate_notification_payload(to, message, raw_type)

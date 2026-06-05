from __future__ import annotations

import re

from notification_service.domain.exceptions import NotificationValidationError
from notification_service.domain.models import NotificationRequest, NotificationType

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
PHONE_PATTERN = re.compile(r"^\+?\d(?:[\d -]{7,14}\d)?$")


def normalize_phone_number(value: str) -> str:
    cleaned = re.sub(r"[ ]+", " ", value.strip())
    if not PHONE_PATTERN.match(cleaned):
        raise NotificationValidationError("Invalid phone number format.")
    return cleaned


def validate_notification_payload(
    to: str,
    message: str,
    raw_type: str,
) -> NotificationRequest:
    recipient = to.strip()
    body = message.strip()
    normalized_type = raw_type.strip().lower()

    if not recipient:
        raise NotificationValidationError("The notification destination is required.")
    if not body:
        raise NotificationValidationError("The notification message is required.")
    if normalized_type not in {NotificationType.EMAIL.value, NotificationType.SMS.value}:
        raise NotificationValidationError("The notification type must be 'email' or 'sms'.")

    notification_type = NotificationType(normalized_type)
    if notification_type is NotificationType.EMAIL:
        if not EMAIL_PATTERN.match(recipient):
            raise NotificationValidationError("Invalid email address format.")
        normalized_recipient = recipient.lower()
    else:
        normalized_recipient = normalize_phone_number(recipient)

    return NotificationRequest(
        to=normalized_recipient,
        message=body,
        type=notification_type,
    )

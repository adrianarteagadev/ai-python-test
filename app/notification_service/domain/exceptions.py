class NotificationServiceError(Exception):
    """Base exception for the notification service."""


class RequestNotFoundError(NotificationServiceError):
    """Raised when a request id does not exist."""


class ExtractionParseError(NotificationServiceError):
    """Raised when the AI response cannot be converted into a valid payload."""


class NotificationValidationError(NotificationServiceError):
    """Raised when a parsed notification payload is invalid."""


class ProviderRetryableError(NotificationServiceError):
    """Raised for transient provider failures that can be retried."""


class ProviderResponseError(NotificationServiceError):
    """Raised for non-retryable provider errors."""

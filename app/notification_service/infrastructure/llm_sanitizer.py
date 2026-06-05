from __future__ import annotations

import ast
import json
import re

from notification_service.domain.exceptions import ExtractionParseError, NotificationValidationError
from notification_service.domain.models import ExtractionResult
from notification_service.domain.validators import validate_notification_payload

FIELD_ALIASES = {
    "to": "to",
    "recipient": "to",
    "destination": "to",
    "message": "message",
    "body": "message",
    "text": "message",
    "type": "type",
    "channel": "type",
    "method": "type",
}
REFUSAL_MARKERS = (
    "i cannot process",
    "lo siento",
    "refused:",
    "potential spam",
    "sensitive information",
)


class LlmResponseSanitizer:
    def parse(self, raw_content: str) -> ExtractionResult:
        cleaned_content = raw_content.strip()
        if not cleaned_content:
            raise ExtractionParseError("The AI provider returned an empty response.")

        candidate = self._extract_candidate(cleaned_content)
        payload = self._load_payload(candidate)
        normalized = self._normalize_payload(payload)

        try:
            notification = validate_notification_payload(
                normalized["to"],
                normalized["message"],
                normalized["type"],
            )
        except KeyError as exc:
            missing_key = exc.args[0]
            raise ExtractionParseError(
                f"The AI response is missing the '{missing_key}' field."
            ) from exc
        except NotificationValidationError as exc:
            raise ExtractionParseError(str(exc)) from exc

        return ExtractionResult(raw_content=cleaned_content, notification=notification)

    def _extract_candidate(self, raw_content: str) -> str:
        fenced_match = re.search(
            r"```(?:json)?\s*(\{[\s\S]*?\})\s*```",
            raw_content,
            flags=re.IGNORECASE,
        )
        if fenced_match:
            return fenced_match.group(1).strip()

        inline_object = self._extract_balanced_braces(raw_content)
        if inline_object is not None:
            return inline_object

        lowered = raw_content.lower()
        if any(marker in lowered for marker in REFUSAL_MARKERS):
            raise ExtractionParseError("The AI provider refused to extract the notification data.")

        raise ExtractionParseError("No JSON object was found in the AI response.")

    @staticmethod
    def _extract_balanced_braces(text: str) -> str | None:
        start_index = text.find("{")
        if start_index < 0:
            return None

        depth = 0
        for index in range(start_index, len(text)):
            character = text[index]
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    return text[start_index : index + 1]
        return None

    def _load_payload(self, candidate: str) -> dict[str, object]:
        normalized_candidate = self._quote_unquoted_keys(candidate)
        try:
            payload = json.loads(normalized_candidate)
        except json.JSONDecodeError:
            try:
                payload = ast.literal_eval(normalized_candidate)
            except (ValueError, SyntaxError) as exc:
                raise ExtractionParseError("The AI response could not be parsed as JSON.") from exc

        if not isinstance(payload, dict):
            raise ExtractionParseError("The AI response must contain a JSON object.")
        return payload

    @staticmethod
    def _quote_unquoted_keys(candidate: str) -> str:
        return re.sub(
            r'([{,]\s*)([A-Za-z_][A-Za-z0-9_\-]*)(\s*:)',
            r'\1"\2"\3',
            candidate,
        )

    def _normalize_payload(self, payload: dict[str, object]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for raw_key, raw_value in payload.items():
            canonical_key = FIELD_ALIASES.get(str(raw_key).strip().lower())
            if canonical_key is None or raw_value is None:
                continue
            normalized[canonical_key] = str(raw_value).strip()

        return normalized

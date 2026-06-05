from pydantic import BaseModel, field_validator

from notification_service.domain.models import RequestStatus


class CreateRequestPayload(BaseModel):
    user_input: str

    @field_validator("user_input")
    @classmethod
    def validate_user_input(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("user_input must not be empty.")
        return normalized_value


class CreateRequestResponse(BaseModel):
    id: str


class RequestStatusResponse(BaseModel):
    id: str
    status: RequestStatus

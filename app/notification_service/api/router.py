from fastapi import APIRouter, Depends, HTTPException, Response, status

from notification_service.api.dependencies import get_container
from notification_service.api.schemas import (
    CreateRequestPayload,
    CreateRequestResponse,
    RequestStatusResponse,
)
from notification_service.application.services import ProcessTriggerOutcome
from notification_service.domain.exceptions import RequestNotFoundError

router = APIRouter(prefix="/v1")


@router.post(
    "/requests",
    response_model=CreateRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_request(payload: CreateRequestPayload, container=Depends(get_container)):
    created_request = await container.request_service.create_request(payload.user_input)
    return CreateRequestResponse(id=created_request.id)


@router.post(
    "/requests/{request_id}/process",
    response_model=RequestStatusResponse,
)
async def process_request(
    request_id: str,
    response: Response,
    container=Depends(get_container),
):
    try:
        result = await container.request_service.trigger_processing(request_id)
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if result.outcome is ProcessTriggerOutcome.ALREADY_SENT:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_202_ACCEPTED

    request = await container.request_service.get_request(request_id)
    return RequestStatusResponse(id=request.id, status=request.status)


@router.get(
    "/requests/{request_id}",
    response_model=RequestStatusResponse,
)
async def get_request(request_id: str, container=Depends(get_container)):
    try:
        request = await container.request_service.get_request(request_id)
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RequestStatusResponse(id=request.id, status=request.status)

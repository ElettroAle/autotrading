from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.notifications.request_link_code import IssuedLinkCode


class LinkCodeResponse(BaseModel):
    """The code the user sends to the bot from the chat to link, until when it is valid, and the link that sends it
    in one tap; no link while the bot is not active (R1.8.1)."""

    code: str
    expires_at: datetime
    link: str | None

    @classmethod
    def of(cls, issued: IssuedLinkCode) -> LinkCodeResponse:
        return cls(code=issued.code, expires_at=issued.expires_at, link=issued.link)


class LinkedChatResponse(BaseModel):
    linked: bool


def telegram_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/telegram", tags=["notifiche Telegram"])

    @router.post("/link-code", status_code=status.HTTP_201_CREATED)
    def request_link_code(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> LinkCodeResponse:
        return LinkCodeResponse.of(use_cases.request_link_code.execute())

    @router.get("/chat")
    def read_linked_chat(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> LinkedChatResponse:
        return LinkedChatResponse(linked=use_cases.get_linked_chat.execute() is not None)

    @router.delete("/chat", status_code=status.HTTP_204_NO_CONTENT)
    def unlink_chat(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> None:
        use_cases.unlink_chat.execute()

    return router

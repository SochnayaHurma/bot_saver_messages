from typing import Any

from fastapi import Query, Depends, Body

from db.mongo_client import MessageManager
from models import MessageIn, ListMessagesOut
from service import MessageService


async def get_message_service() -> MessageService:
    db_manager = MessageManager()
    return MessageService(db_manager)


async def get_messages(
    page: int = Query(default=1),
    service: MessageService = Depends(get_message_service)
) -> ListMessagesOut:
    return await service.all(page)


async def create_message(
    message: MessageIn = Body(),
    service: MessageService = Depends(get_message_service)
) -> Any:
    return await service.create(message)

from typing import Any

from models import MessageIn, MessageOut, ListMessagesOut
from db.mongo_client import MessageManager

from utils import paginate


class MessageService:
    def __init__(self, db_connect: MessageManager):
        self.db = db_connect

    async def all(self, page: int = 1) -> ListMessagesOut:
        count_messages = await self.db.count()
        pages = paginate(page, count_messages)
        messages = [
            MessageOut(
                name=row.get('name'),
                message=row.get('message'),
                date=row.get('date')
            )
            for row in await self.db.all(pages.get('skip'), pages.get('limit'))
        ]
        return ListMessagesOut(
            current_page=page,
            limit=pages.get('limit'),
            last_page=pages.get('last_page'),
            messages=messages
        )

    async def create(self, message: MessageIn) -> Any:
        return await self.db.insert(
            date=message.date,
            name=message.name,
            message=message.message
        )

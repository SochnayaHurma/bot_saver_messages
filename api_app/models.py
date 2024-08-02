from datetime import datetime

from pydantic import BaseModel


class MessageIn(BaseModel):
    name: str
    message: str
    date: datetime


class MessageOut(BaseModel):
    name: str
    message: str
    date: datetime


class ListMessagesOut(BaseModel):
    current_page: int
    last_page: int
    limit: int
    messages: list[MessageOut]

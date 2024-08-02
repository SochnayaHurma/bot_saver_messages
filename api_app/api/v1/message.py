from fastapi import APIRouter, Depends, status

from api.v1.dependencies import get_messages, create_message
from models import ListMessagesOut

router = APIRouter(tags=['message'])


@router.get('/messages/', response_model=ListMessagesOut)
async def get_messages(messages: ListMessagesOut = Depends(get_messages)):
    """
    Показывает список сообщений по опциональному параметру ?page=int
    """
    return messages


@router.post('/message/', status_code=status.HTTP_201_CREATED)
async def save_message(_=Depends(create_message)):
    """
    Сохраняет сообщение в базе данных по JSON телу
    """
    return None

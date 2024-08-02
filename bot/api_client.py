import os
from datetime import datetime

from httpx import AsyncClient

from config import settings
from formaters import format_messages


async def fetch_page_messages(page: int = 1):
    async with AsyncClient(base_url=settings.API_URL) as client:
        response = await client.get(
            '/api/v1/messages/',
            params={'page': page}
        )
        converted_response = response.json()
        messages = converted_response.get('messages', [])
    return {
        'current_page': converted_response.get('current_page'),
        'last_page': converted_response.get('last_page'),
        'messages': format_messages(messages)
    }


async def fetch_create_message(
        name: str,
        message: str,
        date: datetime
):
    async with AsyncClient(base_url=settings.API_URL) as client:
        detail = await client.post(
            '/api/v1/message/',
            json={'name': name, 'message': message, 'date': str(date)})

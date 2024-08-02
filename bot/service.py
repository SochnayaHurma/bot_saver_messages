from aiogram.fsm.context import FSMContext

from api_client import fetch_page_messages, fetch_create_message
from formaters import format_response
from utils import get_next_page


async def get_messages_to_page(state: FSMContext, action: str = 'default'):
    cache = await state.get_data()
    previous_page = cache.get('current_page', 1)
    current_page = get_next_page(previous_page, action)
    cache_messages = cache.get(f'message:{current_page}')
    if cache_messages:
        await state.update_data({'current_page': current_page})
        return cache_messages

    response = await fetch_page_messages(current_page)
    current_page, last_page = response.get("current_page", 1), response.get("last_page", 1)
    messages = format_response(response.pop('messages'), current_page, last_page)
    await state.update_data({
        **response,
        f'message:{current_page}': messages}
    )
    return messages


async def create_message(name, message, date, state: FSMContext):
    await state.clear()
    await fetch_create_message(name, message, date)

from aiogram.fsm.context import FSMContext

from api_client import fetch_page_messages, fetch_create_message


async def get_messages_to_page(state: FSMContext, action: str = 'default'):
    cache = await state.get_data()
    current_page = cache.get('current_page', 1)
    match action:
        case 'up':
            current_page += 1
        case 'down' if current_page > 1:
            current_page -= 1
        case _:
            current_page = 1
    cache_messages = cache.get(f'message:{current_page}')
    if cache_messages:
        await state.update_data({'current_page': current_page})
        return cache_messages

    response = await fetch_page_messages(current_page)
    messages = response.pop('messages')
    await state.update_data({
        **response,
        f'message:{current_page}': messages}
    )
    return messages


async def create_message(name, message, date, state: FSMContext):
    await state.clear()
    await fetch_create_message(name, message, date)


# Телеграм Bot

# Сформируем структуру папок Bot
#### ├────── routers 
#### ├───────── message.py роутер сообщений
#### ├── api-client.py Запросы к api
#### ├── buttons.py виджеты кнопок
#### ├── formatters.py преобразование текстовых данных
#### ├── main.py точка входа бота
#### ├── service.py бизнес логика запросов
#### ├── config.py конфигурация бота
#### ├── utils.py вспомогательные функции

Точка входа `main.py`
- Занимается инициализацией дополнительных модулей и запуском экземпляра бота
- Обращаемся к текущему логеру и ставим уровень логирования INFO и вывод в консоль
  (на продакшн можно поменять на блокнот или веб систему логирования)
```python
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from config import settings
from routers.message import router as message_router


async def main() -> None:
    bot = Bot(token=settings.TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)
    dp.include_router(message_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

```

#### Запросы
модуль `api-client.py`
- Осуществляет запросы к нашему API базовый адрес, который задается в конфигурации
```python
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
```

#### Преобразование 
модуль `formatters.py`
- Преобразование происходит с помощью генераторного выражения, преобразующего
наш массив данных в единную строку
```python
from typing import TypeAlias

from aiogram import html


template = 'Имя:{name}\nСообщение:{text}\nДата:{date}'
line = '─' * 32

Message: TypeAlias = dict[str, str]


def format_messages(messages: list[Message]) -> str:
    if not messages:
        return html.bold('Сообщений пока нет :(')
    return f'\n{line}\n'.join(
        template.format(
            name=html.bold(message.get('name')),
            text=html.blockquote(message.get('message')),
            date=html.underline(message.get('date'))
        )
        for message in messages[::-1]
    )


def format_response(response: str, current_page: int, last_page: int) -> str:
    pagination_info = html.bold(f'Страница: {current_page} из {last_page}')
    return f'{response}\n{pagination_info}'

```

#### Кэширование и сбор данных
модуль `service.py`

- Запрос на получение страницы включает в себя:
1. Проверка кэша на наличие текущей страницы
2. Проверка намеренья page-up or page-down
   (В обязательной мере ставим стандартное значение)
3. Проверяем наличие кэша с страницей которую хотим получить
4. Если её нет делаем запрос
- Запрос на создание сообщения
1. Очистку кэша
2. Отправка запроса на сохранение сообщения

модуль `service.py`
```python
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

```

#### Запрос будущих страниц
- Запрос будущих страниц будем осуществлять через inline кнопки
  (т.к логику можно заменить не на отправку сообщение, а обновление существующего, 
  но при этом нужно проверять изменилась ли страница, а то телеграм ругается)
```python
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def paginate_buttons():
    kb_list = [
        [InlineKeyboardButton(text="Предыдущая", callback_data='1')],
        [InlineKeyboardButton(text="Следующая", callback_data='2')]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_list)
    return keyboard

```
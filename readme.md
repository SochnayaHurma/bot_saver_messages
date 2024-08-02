##### Оставил `.env` файл для тестов 

# API
# Сформируем структуру папщк API
#### ├── api
#### ├───── v1
#### ├───────── message.py
#### ├───────── dependencies.py
#### ├── models.py
#### ├── main.py 
#### ├── config.py
#### ├── utils.py
## Получение данных(снизу вверх)
#### Подключение
Подключением к базе данных mongodb будет заниматься модуль motor,
который предоставляет асинхронный клиент
`poetry add motor`

#### Запросы
Логику получения данных из api поделим на несколько частей
1. Data. Вывод чистых строчек с базы данных

- Сборщика данных назовем MessageManager, который в конструкторе будет выполнять подключение к бд
(без обработки ошибок)
- Методы будут принимать примитивы(для отделяемости)
```python
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from config import settings


class MessageManager:
    def __init__(self, collection: str = settings.db.COLLECTION_NAME) -> None:
        self.client = AsyncIOMotorClient(settings.db.MONGODB_URL)
        self.database: AsyncIOMotorDatabase = self.client.get_database(settings.db.DB_NAME)
        self.collection: AsyncIOMotorCollection = self.database.get_collection(collection)

    async def all(self, offset: int, limit: int, sort: str = 'date') -> list:
        cursor = self.collection.find().sort({sort: -1})
        if offset:
            cursor.skip(offset)
        return await cursor.to_list(limit)

    async def insert(self, date, name, message):
        return await self.collection.insert_one({
            'date': date,
            'name': name,
            'message': message
        })

    async def count(self, **kwargs):
        return await self.collection.count_documents(kwargs)

```
2. Service. Выполнение безнес логики и преобразование в схемы
- Бизнес логику у нас будет осуществлять класс MessageService
- Принимать в аргументы источник данных(хорошо бы иметь как тип базовый класс для независимости от источника)
```python
from typing import Any

from models.message import MessageIn, MessageOut, ListMessagesOut
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

```
3. Dependency. Сбор зависимостей связанных с web и делегирование слою service
- Сбор зависимостей с пользовательского запроса
- get_message_service не так уж обязателен, но если проект сделать посерьезней нам
необходимы будут обработки ошибок подключений retry или альтернативный источник данных
  (можно заменить lifespan)

модуль `api/v1/dependencies.py`
```python
from typing import Any

from fastapi import Query, Depends, Body

from db.mongo_client import MessageManager
from models.message import MessageIn, ListMessagesOut
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

```

#### Составим модель 
- Схема для ввода(создания) записи мы будем использовать модель MessageIn
- Схема для вывода записей мы будем использщовать MessageOut
- Схема содержающая текущую страницу, последнюю страницу и список сообщений


модуль `models.py`
```python
from pydantic import BaseModel

class MessageIn(BaseModel):
    id: int
    name: str
    message: str


class MessageOut(BaseModel):
    name: str
    message: str
    

class ListMessagesOut(BaseModel):
    current_page: int
    last_page: int
    limit: int
    messages: list[MessageOut]

```
#### Маршруты
- От первого(GET) маршрута ожидаем стандартный ответ 200 по схеме ListMessagesOut
- От второго(POST) маршрута ожидаем статус 201_Created сигнализирующее о успешном создании сущности

модуль `routers/message.py`
```python
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

```

#### Config

Чтобы гарантировать, что приложение стартовало подхватив все наши переменные окружения
установим `pydantic_settings`
`poetry add pydantic_settings`

- Разделим на кусочки наши конфигурации для легкой тестируемости

модуль `config.py`
```python
from pydantic_settings import BaseSettings


class MongoDBSettings(BaseSettings):
    MONGODB_URL: str = 'mongodb://root:example@localhost:27017'
    DB_NAME: str = 'tg_bot'
    COLLECTION_NAME: str = 'message'


class PaginationSettings(BaseSettings):
    MAX_ROWS: int = 10


class Settings(BaseSettings):
    db: MongoDBSettings = MongoDBSettings()
    pagination: PaginationSettings = PaginationSettings()


settings = Settings()

```
#### Пагинация 
- Стартовую запись мы вычисляем по формуле
  (Всего записей * (Ожидаемая страница - 1)), 
- Последнюю страницу мы вычисляем по формуле
  (Всего записей / максимальное кол-во записей на странице)
  и если есть знаки после запятой т.е. последние записи мы выделяем им тоже страницу
  округлив число до большего
- Дальше следуют охранные условия
1. Если количество заисей с которых мы хотим начать выборку больше, чем
кол-во записей в бд, то мы отдаем последние 10 строчек из бд и назначаем текущую страницу
последней
2. Если последняя страница это первая, то мы назначаем текущую страницу первой
и количество записей, которые нужно пропустить обнуляем

модуль `utils.py`
```python
import math

from config import settings


def paginate(
        expected_page: int,
        count_db_rows: int,
        max_rows: int = settings.pagination.MAX_ROWS
):
    per_page = max_rows * (expected_page - 1)
    last_page = math.ceil(count_db_rows / max_rows)
    if per_page >= count_db_rows:
        per_page = count_db_rows - max_rows
        expected_page = last_page
    if last_page <= 1:
        expected_page = last_page = 1
        per_page = 0
    return {
        'current_page': expected_page,
        'skip': per_page,
        'limit': max_rows,
        'last_page': last_page
    }
```

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
```

#### Преобразование 
модуль `formatters.py`
- Преобразование происходит с помощью генераторного выражения, преобразующего
наш массив данных в единную строку
```python
from typing import TypeAlias

from aiogram import html


template = 'Имя:{name}\nСообщение:{text}\nДата:{date}\n\n'

Message: TypeAlias = dict[str, str]


def format_messages(messages: list[Message]) -> str:
    if not messages:
        return html.bold('Сообщений пока нет :(')
    return '\n\n'.join(
        template.format(
            name=html.bold(message.get('name')),
            text=html.blockquote(message.get('message')),
            date=html.underline(message.get('date'))
        )
        for message in messages[::-1]
    )

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
```python
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
# Объединяем кусочки в комок 
#### nginx
- Монтируем базовые конфигурации из папки templates
- Монтируем директорию, где будут хранится сокеты gunicorn 
- Пробрасываем порт 80 443

```yaml
services:
  nginx:
    image: nginx
    ports:
      - 80:80
      - 443:443
    volumes:
      - "./docker/nginx/template:/etc/nginx/templates:ro"
      - "./docker/nginx/socket/:/tmp/socket:rw"
```

#### api

- Переменные среды берем из файла .env
- Монтируем директорию для сокетов чтобы пробросить их nginx
```yaml
  api:
    build:
      context: .
      dockerfile: ./docker/api/Dockerfile
    env_file:
      - ./.env
    volumes:
      - "./docker/nginx/socket:/tmp/socket:rw"
```

#### bot 
- Указываем переменные среды
```yaml
  bot:
    build:
      context: .
      dockerfile: ./docker/bot/Dockerfile
    env_file:
      - ./.env
```
#### MongoDB
- Пробрасываем порт 27017
- Указываем переменные среды 

```yaml
  mongo:
    image: mongo
    restart: always
    ports:
      - 27017:27017
    env_file: './.env'
```
#### Redis 
- Указываем переменные среды
- При старте задаем sh скрипт, который:
1. Создает директорию для redis.conf
2. Заполняет redis.conf базовыми конфигурациями 
3. "Регистрирует нового пользователя" с указанными данными из переменных среды
```yaml
  redis:
    build:
      dockerfile: './docker/redis/Dockerfile'
    env_file: './.env'
    command: >
      sh -c '
        mkdir -p /usr/local/etc/redis &&
        echo "bind 0.0.0.0" > /usr/local/etc/redis/redis.conf &&
        echo "requirepass $REDIS_PASSWORD" >> /usr/local/etc/redis/redis.conf &&
        echo "appendonly yes" >> /usr/local/etc/redis/redis.conf &&
        echo "appendfsync everysec" >> /usr/local/etc/redis/redis.conf &&
        echo "user default on nopass ~* +@all" > /usr/local/etc/redis/users.acl &&
        echo "user $REDIS_USER on >$REDIS_USER_PASSWORD ~* +@all" >> /usr/local/etc/redis/users.acl &&
        redis-server /usr/local/etc/redis/redis.conf --aclfile /usr/local/etc/redis/users.acl
      '
    ports:
      - "6379:6379"
    restart: unless-stopped
```
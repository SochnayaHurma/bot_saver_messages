# API
# Сформируем структуру папок API
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
##### 1. Data. Вывод чистых строчек с базы данных

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
##### 2. Service. Выполнение безнес логики и преобразование в схемы
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
            current_page=pages.get('current_page'),
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
##### 3. Dependency. Сбор зависимостей связанных с web и делегирование слою service
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

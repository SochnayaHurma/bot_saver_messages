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


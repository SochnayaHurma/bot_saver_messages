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

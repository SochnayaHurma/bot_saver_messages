from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TOKEN: str
    REDIS_URL: str
    API_URL: str = 'http://localhost'


settings = Settings()

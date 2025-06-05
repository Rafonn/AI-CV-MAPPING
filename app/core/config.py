import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

class Settings(BaseSettings):
    load_dotenv()

    MONGODB_URL: str = os.getenv('MONGODB_URL')
    MONGODB_DATABASE_NAME: str = os.getenv('MONGODB_DATABASE_NAME')

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
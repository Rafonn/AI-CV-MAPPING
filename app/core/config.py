from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb+srv://rafael:Mpo69542507@cvcluster.6lt4vep.mongodb.net/?retryWrites=true&w=majority&appName=CvCLUSTER"
    MONGODB_DATABASE_NAME: str = "resume_screener_db"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
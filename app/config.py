import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # База данных
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    # JWT
    SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-it")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

    # GigaChat
    GIGACHAT_API_URL = os.getenv("GIGACHAT_API_URL", "https://gigachat.devices.sberbank.ru/api/v1/chat/completions")
    GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID", "")
    GIGACHAT_SECRET = os.getenv("GIGACHAT_SECRET", "")
    GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS", "")


settings = Settings()
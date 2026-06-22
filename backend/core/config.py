import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL")

settings = Settings()
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    IGDB_CLIENT_ID = os.getenv("IGDB_CLIENT_ID") # 트위치 개발자 API 키
    IGDB_ACCESS_TOKEN = os.getenv("IGDB_ACCESS_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/speccheck")

settings = Settings()
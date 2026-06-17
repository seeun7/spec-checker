from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.core.config import settings

# DB 엔진 생성
engine = create_engine(
    settings.DATABASE_URL, 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db(): # 세션 생성
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from backend.core.database import Base

class SoftwareCache(Base):
    #DuckDuckGo로 검색한 정보를 임시 저장하는 DB 캐시 테이블
    
    __tablename__ = "software_cache"

    id = Column(Integer, primary_key=True, index=True)
    software_name = Column(String, unique=True, index=True, nullable=False)
    requirements_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
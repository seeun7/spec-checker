from fastapi import FastAPI
from backend.core.database import engine, Base
from backend.api.routes import router as api_router

# 앱 시작 시 DB 캐시 테이블 자동 생성
Base.metadata.create_all(bind=engine)

# FastAPI 앱 인스턴스 생성
app = FastAPI(title="Spec-Checker")

# 엔드포인트들 메인 앱에 연결
app.include_router(api_router)
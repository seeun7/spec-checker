from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.core.database import engine, Base
from backend.services.agent_graph import spec_agent

# DB 테이블 자동 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Spec-Checker API")

# 클라이언트 요청 데이터 포맷 (Pydantic)
class SpecRequest(BaseModel):
    image_base64: str
    user_spec: str

class SpecResponse(BaseModel):
    software_name: str | None
    result: str

@app.post("/analyze", response_model=SpecResponse)
async def analyze_spec(request: SpecRequest):
    # 클라이언트로부터 이미지와 유저 사양을 받아 LangGraph 워크플로우를 실행합니다.
    
    try: # LangGraph 에이전트에 초기 상태(State) 주입
        initial_state = {
            "image_base64": request.image_base64,
            "user_spec": request.user_spec,
            "software_name": None,
            "is_software": False,
            "requirements_text": None,
            "final_answer": None
        }
        
        # 워크플로우 실행
        result_state = spec_agent.invoke(initial_state)
        
        return SpecResponse(
            software_name=result_state.get("software_name"),
            result=result_state.get("final_answer")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

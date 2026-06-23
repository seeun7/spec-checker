from typing import TypedDict, Optional 
import asyncio # 동기식 DB 호출, 검색 함수가 이벤트 루프 블로킹 방지
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI # 구글 Gemini 모듈
from langchain_core.messages import HumanMessage, SystemMessage
from backend.services.search_service import search_requirements
from backend.models.models import SoftwareCache
from backend.core.database import SessionLocal
from backend.core.config import settings

# 상태(State) 구조체 정의
class AgentState(TypedDict):
    image_base64: str
    user_spec: str
    software_name: Optional[str]
    is_software: bool
    requirements_text: Optional[str]
    final_answer: Optional[str]

llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-flash", 
    api_key=settings.GEMINI_API_KEY, 
    temperature=0.1
)

class VisionResult(BaseModel):
    is_software: bool = Field(description="이미지가 소프트웨어인지 여부")
    software_name: Optional[str] = Field(description="소프트웨어의 정확한 공식 이름. 소프트웨어가 아니면 None")

# 노드 함수 정의 
async def node_analyze_vision(state: AgentState) -> dict: # 이미지가 소프트웨어인지 파악하고 이름을 추출
    sys_msg = SystemMessage(content=(
        "당신은 이미지를 분석하는 AI입니다. "
        "사용자가 올린 이미지가 소프트웨어의 로고, 화면, 스크린샷인지 확인하세요. "
        "정확한 소프트웨어의 이름과 소프트웨어 여부를 판별하여 반환하세요."
    ))
    
    user_msg = HumanMessage(content=[
        {"type": "text", "text": "이 이미지에 나타난 게임/소프트웨어의 이름은 무엇인가요?"},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{state['image_base64']}"}}
    ])
    
    # 구조화된 출력 적용 
    structured_llm = llm.with_structured_output(VisionResult)
    result = await structured_llm.ainvoke([sys_msg, user_msg])
    
    return {
        "is_software": result.is_software, 
        "software_name": result.software_name
    }

async def node_check_db_or_search(state: AgentState) -> dict: # PostgreSQL 캐시를 먼저 확인하고 없으면 웹 검색 후 저장
    software_name = state["software_name"]
    
    # DB 접근 로직 별도 함수로 분리
    def fetch_from_db():
        with SessionLocal() as db:
            return db.query(SoftwareCache).filter(SoftwareCache.software_name == software_name).first()
            
    def save_to_db(req_text):
        with SessionLocal() as db:
            new_cache = SoftwareCache(software_name=software_name, requirements_text=req_text)
            db.add(new_cache)
            db.commit()

    # asyncio.to_thread -> 워커 스레드에서 실행
    cached_data = await asyncio.to_thread(fetch_from_db)
    
    if cached_data:
        print(f"[CACHE HIT] '{software_name}'")
        req_text = cached_data.requirements_text
    else:
        print(f"[CACHE MISS] 검색 및 DB 저장 진행 '{software_name}'")
        req_text = await search_requirements(software_name)
        
        if req_text and "검색 결과를 찾을 수 없습니다" not in req_text:
            await asyncio.to_thread(save_to_db, req_text)
        
    return {"requirements_text": req_text}

async def node_generate_comparison(state: AgentState) -> dict: # 사용자의 PC 사양과 검색된 권장 사양을 비교 분석하여 결과를 생성
    # 시스템 프롬프트
    sys_msg = SystemMessage(content=(
        "당신은 PC 하드웨어 사양을 분석하는 전문가입니다. "
        "아래 규칙을 절대적으로 따르세요."
        "1. MarkDown 기호를 사용하지 마세요."
        "2. 불필요한 인사말이나 추임새, 공감, 부연 설명을 생략하세요."
        "3. 모든 문장의 끝은 '~습니다' 또는 '~합니다'로 간결하게 하세요."
    ))
    # 사용자 프롬프트
    prompt = f"""
    [소프트웨어명]: {state['software_name']}
    [공식 권장 사양]: {state['requirements_text']}
    [사용자 PC 사양]: \n{state['user_spec']}
    
    위 정보를 바탕으로 다음 두 가지 항목만 작성하세요.
    1. 사양 비교표 - 운영체제, CPU, RAM, GPU 항목을 기준 행으로 삼아 사용자 사양과 권장 사양을 비교하는 표를 그리세요.
    2. 최종 분석 결과 - 표 아래에 사용자의 PC 환경에서 해당 소프트웨어를 원활하게 실행할 수 있는지 여부를 간단명료하게 작성하세요. 
    """
    response = await llm.ainvoke([sys_msg, HumanMessage(content=prompt)])
    return {"final_answer": response.content}

async def node_handle_rejection(state: AgentState) -> dict: # 이미지가 소프트웨어가 아닐 경우의 예외 처리 응답
    return {"final_answer": "업로드하신 이미지가 게임이나 소프트웨어 관련 이미지가 아닙니다. 게임 화면이나 로고 이미지를 업로드해 주세요."}

# 라우팅 로직 (조건부 엣지)
def router_is_software(state: AgentState) -> str:
    return "search_node" if state["is_software"] else "rejection_node"

# LangGraph 그래프 빌드 및 연결
workflow = StateGraph(AgentState)

workflow.add_node("vision_node", node_analyze_vision)
workflow.add_node("search_node", node_check_db_or_search)
workflow.add_node("comparison_node", node_generate_comparison)
workflow.add_node("rejection_node", node_handle_rejection)

workflow.set_entry_point("vision_node")

workflow.add_conditional_edges(
    "vision_node", 
    router_is_software,
    {"search_node": "search_node", "rejection_node": "rejection_node"}
)

workflow.add_edge("search_node", "comparison_node")
workflow.add_edge("comparison_node", END)
workflow.add_edge("rejection_node", END)

spec_agent = workflow.compile()
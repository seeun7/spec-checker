from typing import TypedDict, Optional
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

# 노드 함수들 정의
def node_analyze_vision(state: AgentState) -> dict:
    """Vision AI를 사용하여 이미지가 소프트웨어인지 파악하고 이름을 추출합니다."""
    sys_msg = SystemMessage(content=(
        "당신은 이미지를 분석하는 AI입니다. "
        "사용자가 올린 이미지가 게임이나 소프트웨어의 로고, 화면, 스크린샷인지 확인하세요. "
        "맞다면 해당 게임이나 소프트웨어의 '정확한 공식 이름'만 달랑 반환하고, 아니라면 'NOT_SOFTWARE'라고 반환하세요."
    ))
    
    user_msg = HumanMessage(content=[
        {"type": "text", "text": "이 이미지에 나타난 게임/소프트웨어의 이름은 무엇인가요?"},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{state['image_base64']}"}}
    ])
    
    response = llm.invoke([sys_msg, user_msg])
    result_text = response.content.strip()
    
    # Gemini가 가끔 마크다운이나 불필요한 공백을 넣을 수도 있어서 정리하도록 함
    result_text = result_text.replace("```", "").strip()
    
    if "NOT_SOFTWARE" in result_text.upper():
        return {"is_software": False, "software_name": None}
    else:
        return {"is_software": True, "software_name": result_text}

def node_check_db_or_search(state: AgentState) -> dict:
    """PostgreSQL 캐시를 먼저 확인하고, 없으면 웹 검색 후 DB에 저장합니다."""
    software_name = state["software_name"]
    db = SessionLocal()
    
    try:
        cached_data = db.query(SoftwareCache).filter(SoftwareCache.software_name == software_name).first()
        
        if cached_data:
            print(f"[CACHE HIT] DB에서 '{software_name}' 사양 로드 완료")
            req_text = cached_data.requirements_text
        else:
            print(f"[CACHE MISS] DuckDuckGo 검색 및 DB 저장 진행: '{software_name}'")
            req_text = search_requirements(software_name)
            
            new_cache = SoftwareCache(software_name=software_name, requirements_text=req_text)
            db.add(new_cache)
            db.commit()
            
        return {"requirements_text": req_text}
    finally:
        db.close()

def node_generate_comparison(state: AgentState) -> dict:
    """사용자의 PC 사양과 검색된 권장 사양을 비교 분석하여 결과를 생성합니다."""
    sys_msg = SystemMessage(content=(
        "당신은 친절하고 전문적인 PC 하드웨어 전문가입니다. "
        "사용자의 PC가 해당 게임/소프트웨어를 구동할 수 있을지 알기 쉽게 설명해주세요."
    ))
    prompt = f"""
    [소프트웨어명]: {state['software_name']}
    [공식 권장 사양]: {state['requirements_text']}
    [사용자 PC 사양]: \n{state['user_spec']}
    
    위 정보를 바탕으로 해당 소프트웨어가 사용자 PC에서 원활하게 구동될지 비교해서 분석 결과를 작성해주세요.
    """
    response = llm.invoke([sys_msg, HumanMessage(content=prompt)])
    return {"final_answer": response.content}

def node_handle_rejection(state: AgentState) -> dict:
    """이미지가 소프트웨어가 아닐 경우의 예외 처리 응답을 생성합니다."""
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
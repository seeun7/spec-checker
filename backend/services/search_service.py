import asyncio
from duckduckgo_search import DDGS

async def search_requirements(software_name: str) -> str:
    # DuckDuckGo를 이용하여 소프트웨어의 시스템 요구사항 검색

    query = f"{software_name} 공식 시스템 요구사항 PC 권장 사양"
    
    def sync_search():
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=3))
            
    try:
        # 동기식 라이브러리를 사용하지만 백그라운드 스레드에서 실행한 뒤 결과만 비동기로 받아옴
        results = await asyncio.to_thread(sync_search)

        if not results:
            return "검색 결과를 찾을 수 없습니다."
            
        scraped_text = "\n\n".join([f"- {r.get('body', '')}" for r in results])
        return scraped_text

    except Exception as e:
        print(f"Search Error: {e}")
        return "검색 중 오류가 발생했습니다."
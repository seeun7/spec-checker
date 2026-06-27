import asyncio
from ddgs import DDGS

# DuckDuckGo를 이용하여 소프트웨어의 시스템 요구사항 검색
async def search_requirements(software_name: str) -> str: 

    queries = [
        f"{software_name} pc system requirements",      # 1: 영문 검색
        f"{software_name} minimum specifications pc",   # 2: 영문 최소 사양 검색
        f"{software_name} PC 시스템 권장 사양"            # 3: 한국어 검색
    ]
    
    def sync_search():
        with DDGS() as ddgs:
            all_results = []
            for query in queries:
                results = list(ddgs.text(query, max_results=4)) 
                if results:
                    all_results.extend(results)
                    break
            return all_results  
        
    try:
        results = await asyncio.to_thread(sync_search)
        
        if not results:
            return "검색 결과를 찾을 수 없습니다. 이름이 정확한지 확인해 주세요."
            
        # 웹 검색 요약 텍스트를 하나로 결합
        scraped_text = "\n\n".join([f"- {r.get('body', '')}" for r in results])
        return scraped_text

    except Exception as e:
        print(f"Search Error: {e}")
        return "검색 중 오류가 발생했습니다."
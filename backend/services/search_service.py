from duckduckgo_search import AsyncDDGS

async def search_requirements(software_name: str) -> str: # DuckDuckGo를 이용하여 소프트웨어의 시스템 요구사항 검색

    query = f"{software_name} 공식 시스템 요구사항 PC 권장 사양"
    
    try:
        async with AsyncDDGS() as ddgs:
            results = await ddgs.atext(query, max_results=3)
        
        if not results:
            return "검색 결과를 찾을 수 없습니다."
            
        # 검색된 웹페이지들의 요약 텍스트를 하나로 결합
        scraped_text = "\n\n".join([f"- {r['body']}" for r in results])
        return scraped_text

    except Exception as e:
        print(f"Search Error: {e}")
        return "검색 중 오류가 발생했습니다."
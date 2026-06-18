# Spec-Checker
📍PC 프로그램(애플리케이션) 아이콘 또는 이름만을 입력받아 해당 프로그램이 사용자의 PC 환경에서 원활히 실행 가능한지 진단해주는 스펙 체커(Spec-Checker)프로그램  

### 사용 기술


### 주요 트러블슈팅  
#### 1. LLM API 404 NOT FOUND 에러
- 초기 OPENAI를 이용해 구현했으나 반복되는 404 에러로 제미나이 모델으로 시도
```
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash", 
    api_key=settings.GEMINI_API_KEY, 
    temperature=0.1
)
``` 
- 마찬가지로 404 에러 발생. 해당 부분에 model API를 v1beta 버전에서 찾을 수 없다는 오류 메시지  
i. API KEY 문제인가? -> Google AI Studio에서 확인(정상적으로 발급된 상태)  
ii. model의 이름 문제인가? -> 우선 오타가 아님을 확인  
```
curl "https://generativelanguage.googleapis.com/v1/models?key="내 제미나이 API 키"
```
- 터미널에 입력 -> 구글 API 서버에 현재 가용한 키 목록 반환 받음 -> 반환받은 키 목록에서 "name" 확인  
```"name": "models/gemini-2.5-flash"
"name": "models/gemini-2.5-pro"
```
- model 변수에 입력한 이름과 완전히 같지 않아 models/ + 버전 이름 변경 -> 정상 작동

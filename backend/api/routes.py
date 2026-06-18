from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from backend.services.agent_graph import spec_agent
import traceback
import base64
import platform
import psutil

# Windows 환경에서 GPU 정보를 가져오기 위한 WMI 모듈 설정
try:
    import wmi
    HAS_WMI = True
except ImportError:
    HAS_WMI = False

router = APIRouter()

def get_system_specs() -> str:
    """웹 서버가 실행 중인 로컬 PC의 하드웨어 정보를 추출합니다."""
    os_info = f"{platform.system()} {platform.release()}"
    cpu_info = platform.processor()
    ram_info = round(psutil.virtual_memory().total / (1024**3), 2)
    
    gpu_info = "알 수 없음"
    if HAS_WMI and platform.system() == "Windows":
        try:
            w = wmi.WMI()
            gpus = w.Win32_VideoController()
            if gpus:
                gpu_info = gpus[0].Name
        except Exception:
            gpu_info = "GPU 인식 실패"
    
    return f"[운영체제] {os_info}\n[CPU] {cpu_info}\n[RAM] {ram_info} GB\n[GPU] {gpu_info}"

# 메인 웹페이지(HTML) 렌더링 
@router.get("/", response_class=HTMLResponse)
async def read_root():
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SpecCheck AI 웹 버전</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 40px; display: flex; flex-direction: column; align-items: center; }
            .container { background-color: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 600px; text-align: center; }
            h1 { color: #2c3e50; margin-bottom: 20px; }
            .upload-box { border: 2px dashed #3498db; padding: 40px; border-radius: 8px; margin-bottom: 20px; cursor: pointer; transition: 0.3s; display: block; }
            .upload-box:hover { background-color: #f0f8ff; }
            input[type="file"] { display: none; }
            .btn { background-color: #3498db; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 6px; cursor: pointer; transition: 0.3s; font-weight: bold; width: 100%; }
            .btn:hover { background-color: #2980b9; }
            #loading { display: none; margin-top: 20px; color: #e67e22; font-weight: bold; }
            #result-box { margin-top: 30px; text-align: left; background-color: #f9f9f9; padding: 20px; border-radius: 8px; border-left: 5px solid #2ecc71; display: none; white-space: pre-wrap; line-height: 1.6;}
            .img-preview { max-width: 100%; max-height: 250px; margin-top: 15px; border-radius: 8px; display: none; margin-left: auto; margin-right: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 Spec-Checker</h1>
            <p>게임이나 소프트웨어 스크린샷을 올리면, 내 PC 사양과 비교해 드립니다!</p>
            
            <form id="uploadForm">
                <label class="upload-box" id="drop-zone">
                    <p id="drop-text">📸 클릭하거나 이미지를 드래그 앤 드롭 하세요!</p>
                    <input type="file" id="imageInput" accept="image/*" required>
                    <img id="preview" class="img-preview" src="#" alt="미리보기">
                </label>
                <button type="submit" class="btn">내 PC 사양으로 분석하기</button>
            </form>
            
            <div id="loading">이미지를 분석하고 웹 검색 중입니다...<br>(약 10~20초 소요될 수 있습니다)</div>
            
            <div id="result-box">
                <h3 id="res-title" style="color: #2c3e50; margin-top: 0;"></h3>
                <div id="res-text"></div>
            </div>
        </div>

        <script>
            const form = document.getElementById('uploadForm');
            const fileInput = document.getElementById('imageInput');
            const preview = document.getElementById('preview');
            const dropText = document.getElementById('drop-text');

            fileInput.addEventListener('change', function() {
                const file = this.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        preview.src = e.target.result;
                        preview.style.display = 'block';
                        dropText.style.display = 'none';
                    }
                    reader.readAsDataURL(file);
                }
            });

            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const file = fileInput.files[0];
                if (!file) return alert('이미지를 선택해주세요!');

                document.getElementById('loading').style.display = 'block';
                document.getElementById('result-box').style.display = 'none';

                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch('/analyze-web', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        document.getElementById('res-title').innerText = "인식된 소프트웨어: " + (data.software_name || "알 수 없음");
                        document.getElementById('res-text').innerText = data.result;
                        document.getElementById('result-box').style.display = 'block';
                    } else {
                        alert("에러 발생: " + data.detail);
                    }
                } catch (err) {
                    alert('서버와 통신 중 오류가 발생했습니다.');
                } finally {
                    document.getElementById('loading').style.display = 'none';
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 브라우저에서 보낸 이미지를 받아서 분석
@router.post("/analyze-web")
async def analyze_spec_web(file: UploadFile = File(...)):
    try:
        print(f"\n[INFO] 웹 브라우저에서 이미지 업로드됨: {file.filename}")
        
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        user_specs = get_system_specs()
        print(f"[INFO] PC 사양 추출 완료:\n{user_specs}")
        
        initial_state = {
            "image_base64": base64_image,
            "user_spec": user_specs,
            "software_name": None,
            "is_software": False,
            "requirements_text": None,
            "final_answer": None
        }
        
        print("[INFO] LangGraph 에이전트 실행 중...")
        result_state = spec_agent.invoke(initial_state)
        
        final_ans = result_state.get("final_answer")
        if not final_ans:
            final_ans = "AI가 응답을 생성하지 못했습니다."

        print("[INFO] 분석 완료- 클라이언트로 반환.")
        return {
            "software_name": result_state.get("software_name"),
            "result": final_ans
        }
        
    except Exception as e:
        print("[백엔드 오류 발생]")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
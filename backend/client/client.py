import platform
import psutil
import requests
import base64
import os
import wmi 

def get_system_specs() -> str:
    """사용자 PC 하드웨어 정보 자동 추출"""
    print("내 시스템 사양을 가져오는 중입니다...")
    
    os_info = f"{platform.system()} {platform.release()}"
    cpu_info = platform.processor()
    ram_info = round(psutil.virtual_memory().total / (1024**3), 2)
    
    gpu_info = "알 수 없음"

    try:
        w = wmi.WMI()
        gpus = w.Win32_VideoController()
        if gpus:
            gpu_info = gpus[0].Name
    except Exception:
        gpu_info = "GPU 인식 실패 (또는 지원하지 않는 환경)"

    specs_summary = (
        f"[운영체제] {os_info}\n"
        f"[CPU] {cpu_info}\n"
        f"[RAM] {ram_info} GB\n"
        f"[GPU] {gpu_info}"
    )
    
    print("\n[내 PC 사양 확인 완료!]")
    print(specs_summary)
    print("-" * 40)
    return specs_summary

def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def main():
    print("Spec-Checker에 오신 것을 환영합니다!")
    user_specs = get_system_specs()
    
    image_path = input("사양을 확인할 프로그램의 이름과 아이콘을 업로드하세요: ").strip('"')
    
    if not os.path.exists(image_path):
        print("[ERROR] 파일을 찾을 수 없습니다. 파일 경로를 다시 확인해 주세요.")
        return

    try:
        print("분석을 요청합니다... (약 10~20초가 소요될 수 있습니다.)")
        base64_image = encode_image_to_base64(image_path)
        
        # FastAPI 서버 주소
        server_url = "http://localhost:8000/analyze"
        
        payload = {
            "image_base64": base64_image,
            "user_spec": user_specs
        }
        
        response = requests.post(server_url, json=payload)
        
        if response.status_code == 200:
            result_data = response.json()
            print("\n=========================================")
            print(f"[인식된 소프트웨어]: {result_data.get('software_name')}")
            print("=========================================")
            print("[분석 결과]")
            print(result_data.get('result'))
            print("=========================================")
        else:
            print(f"[ERROR] 서버 에러 발생: HTTP {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] 서버에 연결할 수 없습니다. 백엔드 서버가 켜져 있는지 확인하세요.")
    except Exception as e:
        print(f"[ERROR] 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
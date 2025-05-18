import os
# from dotenv import load_dotenv # .env 파일 사용 시 주석 해제

# .env 파일 로드 (프로젝트 루트에 .env 파일이 있는 경우)
# load_dotenv()

# DART API 키 (실제 키로 교체하거나 환경 변수에서 가져오세요)
# DART_API_KEY = os.getenv("DART_API_KEY", "YOUR_DART_API_KEY_HERE")
DART_API_KEY = "YOUR_DART_API_KEY_HERE" # 직접 입력 방식 (테스트용, 실제 사용시 환경변수 권장)

# KRX/Naver 관련 URL 등 (필요에 따라 추가)
KRX_BASE_URL = "http://data.krx.co.kr/..."
NAVER_FINANCE_URL = "https.finance.naver.com/item/sise_day.nhn?code={code}"

# SQLite DB 파일명
DB_NAME = "stock_mvp.db"

# 기타 설정
CACHE_TIMEOUT_SECONDS = 3600 # 1시간
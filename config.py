import streamlit as st
import os

# DART API 키: secrets.toml → 환경변수 → 기본값 순으로 로드
DART_API_KEY = (
    st.secrets.get("DART_API_KEY") or
    os.environ.get("DART_API_KEY") or
    "YOUR_DART_API_KEY_HERE"
)

# 캐시 타임아웃 설정 (초 단위)
CACHE_TIMEOUT_SECONDS = 60 * 10  # 기본 10분

# (선택) 향후 확장을 위한 항목
# 예: FIREBASE_API_KEY = st.secrets.get("FIREBASE_API_KEY")
# 예: ENABLE_PREMIUM = st.secrets.get("ENABLE_PREMIUM", False)

import streamlit as st
import os

# DART API 키: secrets.toml → 환경변수 → 기본값 순
DART_API_KEY = (
    st.secrets.get("DART_API_KEY") or
    os.environ.get("DART_API_KEY") or
    "YOUR_DART_API_KEY_HERE"
)

# 캐시 타임아웃 설정 (초 단위)
CACHE_TIMEOUT_SECONDS = 60 * 10  # 10분

# SQLite DB 파일 경로
DB_NAME = "stock_mvp.db"

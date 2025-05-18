

import sqlite3
import config # 수정: from . import config 또는 import config (프로젝트 구조에 따라) -> 여기서는 import config
from utils import get_logger
import datetime

logger = get_logger(__name__)
DB_PATH = config.DB_NAME

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # 컬럼명으로 접근 가능하게
    return conn

def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 사용자 조회 기록 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            company_name TEXT,
            search_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 사용자 설정 테이블 (예시)
        # user_settings 테이블에 'analysis_period_days' 컬럼 추가
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id TEXT PRIMARY KEY,
            theme TEXT DEFAULT 'light',
            favorite_stocks TEXT,  -- JSON 문자열로 저장 (예: '["005930", "035720"]')
            analysis_period_days INTEGER DEFAULT 90 -- 분석 기간 저장용 컬럼 추가
        )
        """)
        
        conn.commit()
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        if conn:
            conn.close()

def save_user_search(user_id: str, stock_code: str, company_name: str = None):
    """사용자의 종목 검색 기록을 저장합니다."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO user_search_history (user_id, stock_code, company_name)
        VALUES (?, ?, ?)
        """, (user_id, stock_code, company_name))
        conn.commit()
        logger.info(f"Saved search for user {user_id}, stock {stock_code}")
    except sqlite3.Error as e:
        logger.error(f"Error saving user search: {e}")
    finally:
        if conn:
            conn.close()

def get_user_history(user_id: str, limit: int = 10):
    """특정 사용자의 최근 검색 기록을 가져옵니다."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT stock_code, company_name, search_timestamp
        FROM user_search_history
        WHERE user_id = ?
        ORDER BY search_timestamp DESC
        LIMIT ?
        """, (user_id, limit))
        history = cursor.fetchall() # Row 객체의 리스트로 반환
        return [dict(row) for row in history] # 사용하기 쉽게 dict 리스트로 변환
    except sqlite3.Error as e:
        logger.error(f"Error fetching user history: {e}")
        return []
    finally:
        if conn:
            conn.close()

# 사용자 설정 저장/조회 함수
def save_user_setting(user_id: str, setting_key: str, setting_value):
    conn = get_db_connection()
    try:
        # user_settings 테이블에 해당 user_id가 없으면 먼저 삽입
        # INSERT OR IGNORE는 user_id가 PK이므로 존재하면 무시, 없으면 삽입.
        conn.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
        
        # 해당 컬럼이 존재하는지 확인하고 없으면 ALTER TABLE로 추가 (주의: 실제 운영에서는 마이그레이션 도구 사용)
        # MVP에서는 user_settings 테이블 생성 시 analysis_period_days 컬럼을 미리 정의해두는 것이 좋음.
        # (init_db 함수에 analysis_period_days 컬럼 추가함)

        # 그 후 업데이트
        # f-string을 사용한 동적 컬럼명은 SQL Injection에 취약할 수 있으나,
        # 여기서는 setting_key가 개발자가 제어하는 값이므로 허용.
        # 만약 setting_key가 사용자 입력에서 온다면 반드시 검증하거나 다른 방식을 사용해야 함.
        conn.execute(f"UPDATE user_settings SET {setting_key} = ? WHERE user_id = ?", 
                     (setting_value, user_id))
        conn.commit()
        logger.info(f"Setting '{setting_key}' saved for user {user_id}")
    except sqlite3.Error as e:
        # 만약 "no such column" 에러가 발생하면, ALTER TABLE로 컬럼 추가 시도 (임시 방편)
        if "no such column" in str(e) and setting_key == "analysis_period_days":
            logger.warning(f"Column {setting_key} not found. Attempting to add it.")
            try:
                conn.execute(f"ALTER TABLE user_settings ADD COLUMN {setting_key} INTEGER") # 타입은 적절히 지정
                conn.commit()
                # 컬럼 추가 후 다시 업데이트 시도
                conn.execute(f"UPDATE user_settings SET {setting_key} = ? WHERE user_id = ?", 
                             (setting_value, user_id))
                conn.commit()
                logger.info(f"Column {setting_key} added and setting saved for user {user_id}")
            except sqlite3.Error as e_alter:
                logger.error(f"Error adding column or saving user setting for {user_id} after alter: {e_alter}")
        else:
            logger.error(f"Error saving user setting for {user_id}: {e}")
    finally:
        if conn:
            conn.close()

def get_user_setting(user_id: str, setting_key: str, default_value=None):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # f-string 컬럼명 사용 시 주의 (setting_key가 신뢰할 수 있는 소스에서 온다고 가정)
        cursor.execute(f"SELECT {setting_key} FROM user_settings WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        # setting_key가 존재하고 row[setting_key] 값이 None이 아닐 때 해당 값을 반환
        if row and setting_key in row.keys() and row[setting_key] is not None:
            return row[setting_key]
        return default_value # 행이 없거나, 컬럼 값이 NULL인 경우 기본값 반환
            
    except sqlite3.Error as e:
        # "no such column" 에러 발생 시 기본값 반환
        if "no such column" in str(e):
            logger.warning(f"Column {setting_key} not found for user {user_id}. Returning default value.")
            return default_value
        logger.error(f"Error getting user setting for {user_id}, key {setting_key}: {e}")
        return default_value
    finally:
        if conn:
            conn.close()

# 애플리케이션 시작 시 DB 초기화 호출
init_db()
import sqlite3
from . import config
from .utils import get_logger
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
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id TEXT PRIMARY KEY,
            theme TEXT DEFAULT 'light',
            favorite_stocks TEXT  -- JSON 문자열로 저장 (예: '["005930", "035720"]')
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

# 사용자 설정 저장/조회 함수 (예시)
def save_user_setting(user_id: str, setting_key: str, setting_value):
    conn = get_db_connection()
    try:
        # user_settings 테이블에 해당 user_id가 없으면 먼저 삽입
        conn.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
        # 그 후 업데이트
        conn.execute(f"UPDATE user_settings SET {setting_key} = ? WHERE user_id = ?", 
                     (setting_value, user_id))
        conn.commit()
        logger.info(f"Setting '{setting_key}' saved for user {user_id}")
    except sqlite3.Error as e:
        logger.error(f"Error saving user setting for {user_id}: {e}")
    finally:
        if conn:
            conn.close()

def get_user_setting(user_id: str, setting_key: str, default_value=None):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {setting_key} FROM user_settings WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[setting_key] if row and row[setting_key] is not None else default_value
    except sqlite3.Error as e:
        logger.error(f"Error getting user setting for {user_id}: {e}")
        return default_value
    finally:
        if conn:
            conn.close()

# 애플리케이션 시작 시 DB 초기화 호출
init_db()
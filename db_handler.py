

import sqlite3
import config
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
        
        # 사용자 설정 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id TEXT PRIMARY KEY,
            theme TEXT DEFAULT 'light',
            favorite_stocks TEXT,
            analysis_period_days INTEGER DEFAULT 90
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
        logger.info(f"Saved search for user {user_id}, stock {stock_code} ({company_name})")
    except sqlite3.Error as e:
        logger.error(f"Error saving user search: {e}")
    finally:
        if conn:
            conn.close()

def get_user_history(user_id: str, limit: int = 10):
    """특정 사용자의 최근 검색 기록을 가져옵니다. (종목 코드 중복 제거, 가장 최근 검색 기준)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 서브쿼리를 사용하여 각 stock_code별 가장 최근 search_timestamp를 찾고,
        # 이를 기준으로 원래 테이블에서 해당 레코드를 가져옴
        # 또한, company_name이 NULL이거나 비어있지 않은 경우를 우선적으로 가져오도록 COALESCE와 CASE 사용
        query = """
        SELECT t1.stock_code, 
               COALESCE(NULLIF(t1.company_name, ''), '이름없음') as company_name, 
               t1.search_timestamp
        FROM user_search_history t1
        INNER JOIN (
            SELECT 
                stock_code, 
                MAX(search_timestamp) as max_ts
            FROM user_search_history
            WHERE user_id = ?
            GROUP BY stock_code
        ) t2 ON t1.stock_code = t2.stock_code AND t1.search_timestamp = t2.max_ts
        WHERE t1.user_id = ? 
        ORDER BY t1.search_timestamp DESC
        LIMIT ?
        """
        cursor.execute(query, (user_id, user_id, limit)) # user_id가 두 번 필요
        
        history = cursor.fetchall()
        logger.debug(f"Fetched user history for {user_id} (limit {limit}): {len(history)} items.")
        return [dict(row) for row in history]
    except sqlite3.Error as e:
        logger.error(f"Error fetching user history for {user_id}: {e}")
        return []
    finally:
        if conn:
            conn.close()

def save_user_setting(user_id: str, setting_key: str, setting_value):
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
        conn.execute(f"UPDATE user_settings SET {setting_key} = ? WHERE user_id = ?", 
                     (setting_value, user_id))
        conn.commit()
        logger.info(f"Setting '{setting_key}' saved for user {user_id} with value '{setting_value}'")
    except sqlite3.Error as e:
        if "no such column" in str(e):
            logger.warning(f"Column {setting_key} not found for user {user_id}. Attempting to add it.")
            try:
                conn.execute(f"ALTER TABLE user_settings ADD COLUMN {setting_key} INTEGER") # 타입은 적절히 지정
                conn.commit()
                conn.execute(f"UPDATE user_settings SET {setting_key} = ? WHERE user_id = ?", 
                             (setting_value, user_id))
                conn.commit()
                logger.info(f"Column {setting_key} added and setting saved for user {user_id}")
            except sqlite3.Error as e_alter:
                logger.error(f"Error adding column or saving user setting for {user_id} after alter: {e_alter}")
        else:
            logger.error(f"Error saving user setting for {user_id}, key {setting_key}: {e}")
    finally:
        if conn:
            conn.close()

def get_user_setting(user_id: str, setting_key: str, default_value=None):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {setting_key} FROM user_settings WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row and setting_key in row.keys() and row[setting_key] is not None:
            logger.debug(f"Retrieved setting '{setting_key}' for user {user_id}: {row[setting_key]}")
            return row[setting_key]
        logger.debug(f"No setting '{setting_key}' found for user {user_id}, returning default: {default_value}")
        return default_value
            
    except sqlite3.Error as e:
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
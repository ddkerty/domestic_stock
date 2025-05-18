import logging
import time
from functools import wraps

# 기본 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_logger(name):
    return logging.getLogger(name)

# 간단한 캐시 데코레이터 (메모리 기반)
_cache = {}
_cache_expiry = {}

def timed_cache(seconds):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 키 생성 시 kwargs도 고려 (순서 보장 위해 정렬)
            key_parts = [func.__name__] + list(args) + \
                        sorted([(k, v) for k, v in kwargs.items()])
            key = tuple(key_parts)
            
            current_time = time.time()
            
            if key in _cache and current_time < _cache_expiry.get(key, 0):
                logger = get_logger(__name__)
                logger.info(f"Cache hit for {key}")
                return _cache[key]
            
            result = func(*args, **kwargs)
            _cache[key] = result
            _cache_expiry[key] = current_time + seconds
            logger = get_logger(__name__)
            logger.info(f"Cache miss for {key}. Storing result.")
            return result
        return wrapper
    return decorator

# 예시: 문자열 날짜 포맷 변환 등 공통 함수
def format_date_string(date_obj, fmt="%Y-%m-%d"):
    return date_obj.strftime(fmt) if date_obj else None
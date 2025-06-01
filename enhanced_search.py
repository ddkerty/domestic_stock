import streamlit as st
import pandas as pd
from typing import Optional, List, Tuple
from data_fetcher import get_krx_stock_list

try:
    from streamlit_searchbox import st_searchbox
except ImportError:
    st.error("🚫 streamlit-searchbox 라이브러리 설치가 필요합니다.")
    st.code("pip install streamlit-searchbox")
    st.info("⬆️ 위 명령어를 터미널에 입력하여 설치 후 앱을 다시 실행해주세요.")
    st.stop()

@st.cache_data(ttl=3600)
def _load_search_data() -> pd.DataFrame:
    """검색을 위한 주식 데이터를 로드하고 캐시합니다."""
    krx_df = get_krx_stock_list()
    if krx_df.empty:
        return pd.DataFrame()
    krx_df['display_name'] = krx_df['Name'] + ' (' + krx_df['Symbol'] + ')'
    return krx_df

def _search_stocks(searchterm: str) -> List[Tuple[str, str]]:
    """입력된 검색어에 따라 주식을 필터링하는 내부 함수"""
    if not searchterm or len(searchterm) < 1:
        return []
    
    stock_df = _load_search_data()
    if stock_df.empty:
        return []
    
    filtered_df = stock_df[
        stock_df['Name'].str.contains(searchterm, case=False, na=False) |
        stock_df['Symbol'].str.contains(searchterm, case=False, na=False)
    ]
    
    results = []
    for _, row in filtered_df.head(15).iterrows():
        results.append((row['display_name'], row['Symbol']))
    
    return results

def unified_stock_search() -> Optional[str]:
    """
    안정성이 강화된 단일 주식 검색 함수.
    데이터 로드 실패 시, 종목 코드를 직접 입력하는 대체(Fallback) 모드를 제공합니다.
    streamlit-searchbox의 다양한 반환값 유형(튜플, 문자열)을 모두 처리합니다.
    """
    stock_df = _load_search_data()

    if stock_df.empty:
        # 데이터 로딩 실패 시 대체 입력창 제공
        st.warning("전체 종목 목록 로딩에 실패하여 종목명 검색을 사용할 수 없습니다.")
        fallback_code = st.text_input(
            "종목 코드를 직접 입력해주세요. (예: 005930)",
            key="fallback_search_input",
            help="💡 분석하고 싶은 6자리 종목코드를 입력 후 Enter를 누르세요."
        )
        if fallback_code and len(fallback_code) == 6 and fallback_code.isdigit():
            return fallback_code
        elif fallback_code:
            st.info("정확한 6자리 숫자로 된 종목코드를 입력해주세요.")
        return None

    # 데이터 로딩 성공 시 자동완성 검색창 표시
    selected_value = st_searchbox(
        search_function=_search_stocks,
        placeholder="회사명 또는 종목코드 입력 (예: 삼성)",
        label="종목 검색",
        help="💡 검색어를 입력하면 관련 종목이 아래에 표시됩니다.",
        key="unified_stock_searchbox",
        default_options=[
            ("삼성전자 (005930)", "005930"),
            ("SK하이닉스 (000660)", "000660"),
            ("LG에너지솔루션 (373220)", "373220"),
            ("카카오 (035720)", "035720"),
        ]
    )
    
    # --- START: 반환값 처리 로직 강화 ---
    if not selected_value:
        return None

    # Case 1: 사용자가 드롭다운에서 선택한 경우 (튜플 반환)
    if isinstance(selected_value, tuple):
        display_name, stock_code = selected_value
        # st.success(f"✅ 선택: **{display_name}**") # 성공 메시지는 한 번만 뜨도록 조건부로 처리 가능
        return stock_code

    # Case 2: 화면이 새로고침된 후 (문자열 반환)
    if isinstance(selected_value, str):
        # "삼성전자 (005930)" 형태의 문자열에서 종목코드만 추출
        if '(' in selected_value and ')' in selected_value:
            try:
                stock_code = selected_value.split('(')[-1].split(')')[0]
                if len(stock_code) == 6 and stock_code.isdigit():
                    return stock_code
            except IndexError:
                # 잘못된 형식의 문자열은 무시
                pass
        
        # 순수한 6자리 종목코드가 입력된 경우
        if len(selected_value) == 6 and selected_value.isdigit():
            return selected_value

    return None
    # --- END: 반환값 처리 로직 강화 ---
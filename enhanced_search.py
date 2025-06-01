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
    UX가 개선된 단일 주식 검색 함수.
    데이터 로드 확인 후, 실패 시 에러 메시지를 표시합니다.
    """
    # 검색창을 띄우기 전에 데이터 로드를 먼저 시도하고 확인합니다.
    stock_df = _load_search_data()

    if stock_df.empty:
        st.error("주식 목록을 불러올 수 없습니다.")
        st.caption("네트워크 연결을 확인하거나, 잠시 후 다시 시도해 주세요. 문제가 지속되면 FinanceDataReader 라이브러리의 상태를 확인해야 할 수 있습니다.")
        return None  # 데이터가 없으면 함수를 여기서 중단

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
    
    if selected_value:
        st.success(f"✅ 선택: **{selected_value[0]}**")
        return selected_value[1] 
    
    return None
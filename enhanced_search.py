import streamlit as st
import pandas as pd
from typing import Optional, List, Tuple
from data_fetcher import get_krx_stock_list

try:
    from streamlit_searchbox import st_searchbox
except ImportError:
    # 이 부분은 라이브러리 설치 후에는 보이지 않게 됩니다.
    st.error("🚫 streamlit-searchbox 라이브러리 설치가 필요합니다.")
    st.code("pip install streamlit-searchbox")
    st.info("⬆️ 위 명령어를 터미널에 입력하여 설치 후 앱을 다시 실행해주세요.")
    st.stop() # 라이브러리가 없으면 아래 코드 실행을 중지

@st.cache_data(ttl=3600)
def _load_search_data() -> pd.DataFrame:
    """검색을 위한 주식 데이터를 로드하고 캐시합니다."""
    krx_df = get_krx_stock_list()
    if krx_df.empty:
        return pd.DataFrame()
    # 검색 및 표시를 위한 'display_name' 컬럼 생성
    krx_df['display_name'] = krx_df['Name'] + ' (' + krx_df['Symbol'] + ')'
    return krx_df

def _search_stocks(searchterm: str) -> List[Tuple[str, str]]:
    """입력된 검색어에 따라 주식을 필터링하는 내부 함수"""
    if not searchterm or len(searchterm) < 1:
        return []
    
    stock_df = _load_search_data()
    if stock_df.empty:
        return []
    
    # 회사명 또는 종목코드에 검색어가 포함된 경우 필터링
    filtered_df = stock_df[
        stock_df['Name'].str.contains(searchterm, case=False, na=False) |
        stock_df['Symbol'].str.contains(searchterm, case=False, na=False)
    ]
    
    # 결과를 (표시용 이름, 실제 종목코드) 튜플 리스트로 반환
    results = []
    for _, row in filtered_df.head(15).iterrows():  # 최대 15개 결과 표시
        results.append((row['display_name'], row['Symbol']))
    
    return results

def unified_stock_search() -> Optional[str]:
    """
    UX가 개선된 단일 주식 검색 함수.
    streamlit-searchbox를 사용하여 자동완성 및 실시간 검색 목록을 제공합니다.
    """
    # 검색창 위젯 실행
    selected_value = st_searchbox(
        search_function=_search_stocks,
        placeholder="회사명 또는 종목코드 입력 (예: 삼성)",
        label="종목 검색",
        help="💡 검색어를 입력하면 관련 종목이 아래에 표시됩니다.",
        key="unified_stock_searchbox",
        default_options=[  # 사용자가 아무것도 입력하지 않았을 때 보여줄 기본 목록
            ("삼성전자 (005930)", "005930"),
            ("SK하이닉스 (000660)", "000660"),
            ("LG에너지솔루션 (373220)", "373220"),
            ("카카오 (035720)", "035720"),
        ]
    )
    
    if selected_value:
        # st_searchbox는 (표시용 이름, 실제 값) 튜플을 반환하므로 실제 값(종목코드)을 추출
        st.success(f"✅ 선택: **{selected_value[0]}**")
        return selected_value[1] 
    
    return None
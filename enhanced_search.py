# enhanced_search.py
# 개선된 주식 검색 기능 구현

import streamlit as st
import pandas as pd
from typing import Optional, Tuple, List
from data_fetcher import get_krx_stock_list, fetch_company_info

@st.cache_data(ttl=3600)  # 1시간 캐시
def get_stock_options() -> Tuple[List[str], dict]:
    """
    주식 목록을 가져와서 검색 가능한 형태로 변환
    Returns:
        options: 표시용 옵션 리스트
        code_mapping: 표시명 -> 종목코드 매핑 딕셔너리
    """
    krx_df = get_krx_stock_list()
    if krx_df.empty:
        return [], {}
    
    # "회사명 (종목코드)" 형태로 옵션 생성
    options = []
    code_mapping = {}
    
    for _, row in krx_df.iterrows():
        display_text = f"{row['Name']} ({row['Symbol']})"
        options.append(display_text)
        code_mapping[display_text] = row['Symbol']
    
    return sorted(options), code_mapping

def stock_search_selectbox() -> Optional[str]:
    """
    방법 1: 기본 selectbox를 사용한 주식 검색
    
    장점:
    - 구현이 간단하고 안정적
    - 내장된 검색 기능 활용
    - 외부 의존성 없음
    
    단점:
    - 대용량 데이터 로딩 시 느림
    - UI 커스터마이징 제한
    """
    st.subheader("📈 기본 주식 검색")
    
    options, code_mapping = get_stock_options()
    
    if not options:
        st.error("주식 목록을 불러올 수 없습니다. 네트워크 연결을 확인해주세요.")
        return None
    
    # selectbox에는 기본적으로 검색 기능이 내장되어 있음
    selected = st.selectbox(
        "회사명 또는 종목코드를 입력하세요",
        options=["선택하세요..."] + options,
        help="💡 회사명의 일부를 입력하면 해당하는 종목들이 자동으로 필터링됩니다.",
        key="basic_selectbox"
    )
    
    if selected and selected != "선택하세요...":
        stock_code = code_mapping[selected]
        st.success(f"✅ 선택된 종목: {selected}")
        st.info(f"🔍 종목코드: {stock_code}")
        return stock_code
    
    return None

def stock_search_dynamic() -> Optional[str]:
    """
    방법 2: 텍스트 입력과 동적 필터링을 사용한 주식 검색
    
    장점:
    - 직관적인 사용자 경험
    - 실시간 검색 결과 표시
    - 맞춤형 UI 가능
    
    단점:
    - 많은 검색 결과 시 UI 복잡
    - 상태 관리 필요
    """
    st.subheader("🔍 동적 주식 검색")
    
    # KRX 주식 목록 가져오기
    krx_df = get_krx_stock_list()
    if krx_df.empty:
        st.error("주식 목록을 불러올 수 없습니다. 네트워크 연결을 확인해주세요.")
        return None
    
    # 검색어 입력
    search_term = st.text_input(
        "회사명 검색", 
        placeholder="예: 삼성, LG, SK, 현대, 카카오...",
        help="💡 회사명의 일부를 입력하면 관련 종목들이 실시간으로 표시됩니다.",
        key="dynamic_search"
    )
    
    if search_term and len(search_term) >= 1:
        # 회사명과 종목코드에서 검색어가 포함된 항목 필터링
        filtered_df = krx_df[
            krx_df['Name'].str.contains(search_term, case=False, na=False) |
            krx_df['Symbol'].str.contains(search_term, case=False, na=False)
        ]
        
        if not filtered_df.empty:
            st.write(f"📋 검색 결과: **{len(filtered_df)}개** 종목 발견")
            
            # 검색 결과가 많은 경우 경고 메시지
            if len(filtered_df) > 20:
                st.warning(f"⚠️ 검색 결과가 {len(filtered_df)}개로 많습니다. 더 구체적인 검색어를 입력해보세요.")
            
            # 헤더
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                st.write("**📊 회사명**")
            with col2:
                st.write("**🏷️ 종목코드**")
            with col3:
                st.write("**✅ 선택**")
            
            st.divider()
            
            # 검색 결과를 버튼으로 표시 (최대 10개)
            for idx, (_, row) in enumerate(filtered_df.head(10).iterrows()):
                col1, col2, col3 = st.columns([4, 2, 1])
                
                with col1:
                    st.write(f"🏢 {row['Name']}")
                with col2:
                    st.code(row['Symbol'])
                with col3:
                    if st.button("선택", key=f"select_{idx}_{row['Symbol']}", type="primary"):
                        st.session_state.selected_stock = {
                            'name': row['Name'],
                            'code': row['Symbol']
                        }
                        st.rerun()
            
            # 더 많은 결과가 있는 경우 메시지 표시
            if len(filtered_df) > 10:
                st.info(f"📢 상위 10개 결과만 표시됩니다. 총 {len(filtered_df)}개 중 {min(10, len(filtered_df))}개 표시")
        
        else:
            st.warning("🔍 검색 결과가 없습니다. 다른 검색어를 시도해보세요.")
            # 검색 도움말
            with st.expander("💡 검색 팁"):
                st.write("""
                - **회사명 일부**: '삼성', 'LG', 'SK' 등
                - **종목코드**: '005930', '000660' 등  
                - **업종명**: '전자', '화학', '금융' 등
                - **한글/영문**: '카카오' 또는 'Kakao'
                """)
    
    # 선택된 종목 표시
    if 'selected_stock' in st.session_state:
        selected = st.session_state.selected_stock
        st.success(f"✅ 선택된 종목: **{selected['name']}** ({selected['code']})")
        
        # 선택 해제 버튼
        if st.button("🔄 선택 해제", key="clear_selection"):
            del st.session_state.selected_stock
            st.rerun()
        
        return selected['code']
    
    return None

def stock_search_advanced() -> Optional[str]:
    """
    방법 3: streamlit-searchbox를 사용한 고급 주식 검색
    
    필요 설치: pip install streamlit-searchbox
    
    장점:
    - 전문적인 자동완성 경험
    - 높은 성능
    - 풍부한 커스터마이징 옵션
    
    단점:
    - 외부 라이브러리 의존성
    - 설정이 복잡할 수 있음
    """
    try:
        from streamlit_searchbox import st_searchbox
    except ImportError:
        st.error("🚫 streamlit-searchbox가 설치되지 않았습니다.")
        st.code("pip install streamlit-searchbox")
        st.info("⬆️ 위 명령어로 설치 후 다시 시도해주세요.")
        return None
    
    st.subheader("🚀 고급 주식 검색")
    
    # KRX 데이터를 로드
    @st.cache_data(ttl=3600)
    def load_stock_data():
        """주식 데이터를 로드하고 캐시"""
        krx_df = get_krx_stock_list()
        if krx_df.empty:
            return pd.DataFrame()
        
        # 검색을 위한 데이터 전처리
        krx_df['display_name'] = krx_df['Name'] + ' (' + krx_df['Symbol'] + ')'
        return krx_df
    
    def search_stocks(searchterm: str) -> List[Tuple[str, str]]:
        """주식 검색 함수"""
        if not searchterm or len(searchterm) < 1:
            return []
        
        stock_df = load_stock_data()
        if stock_df.empty:
            return []
        
        # 회사명과 종목코드에서 검색
        filtered = stock_df[
            stock_df['Name'].str.contains(searchterm, case=False, na=False) |
            stock_df['Symbol'].str.contains(searchterm, case=False, na=False)
        ]
        
        # 결과를 (표시명, 종목코드) 튜플로 반환
        results = []
        for _, row in filtered.head(20).iterrows():  # 최대 20개 결과
            results.append((row['display_name'], row['Symbol']))
        
        return results
    
    # searchbox 컴포넌트 사용
    selected_stock = st_searchbox(
        search_stocks,
        placeholder="회사명 또는 종목코드를 입력하세요 (예: 삼성전자, 005930)",
        label="🔎 종목 검색",
        help="💡 회사명의 일부를 입력하면 자동으로 관련 종목들이 표시됩니다.",
        key="stock_searchbox",
        default_options=[
            ("삼성전자 (005930)", "005930"),
            ("LG에너지솔루션 (373220)", "373220"), 
            ("SK하이닉스 (000660)", "000660"),
            ("카카오 (035720)", "035720"),
            ("NAVER (035420)", "035420")
        ],
        clear_on_submit=False,
        edit_after_submit="current"
    )
    
    if selected_stock:
        # 종목코드 추출 (튜플의 두 번째 요소)
        if isinstance(selected_stock, tuple):
            display_name, stock_code = selected_stock
            st.success(f"✅ 선택된 종목: **{display_name}**")
            return stock_code
        else:
            # 문자열인 경우 (이전 버전 호환성)
            st.success(f"✅ 선택된 종목: **{selected_stock}**")
            return selected_stock
    
    return None

def enhanced_stock_search_main():
    """
    통합 주식 검색 인터페이스
    여러 검색 방법을 제공하고 사용자가 선택할 수 있게 함
    """
    st.title("📊 주식분석 플랫폼 - 개선된 검색")
    
    # 검색 방법 선택
    st.sidebar.header("🔧 검색 설정")
    search_method = st.sidebar.radio(
        "검색 방법 선택",
        ["기본 검색", "동적 검색", "고급 검색"],
        help="""
        **기본 검색**: 간단한 selectbox 방식
        **동적 검색**: 실시간 필터링 방식  
        **고급 검색**: 전문 자동완성 방식
        """
    )
    
    # 선택된 방법에 따라 다른 검색 인터페이스 표시
    selected_stock_code = None
    
    if search_method == "기본 검색":
        selected_stock_code = stock_search_selectbox()
    elif search_method == "동적 검색":
        selected_stock_code = stock_search_dynamic()
    elif search_method == "고급 검색":
        selected_stock_code = stock_search_advanced()
    
    # 결과 표시
    if selected_stock_code:
        st.divider()
        st.write(f"🎯 선택된 종목코드: **{selected_stock_code}**")
        
        # 여기에 기존의 주식 분석 로직을 연결
        st.info("💡 이제 이 종목코드를 사용해서 기존의 분석 기능들을 실행할 수 있습니다!")
        
        # 예시: 기업 정보 표시
        try:
            company_info = fetch_company_info(selected_stock_code)
            if company_info:
                st.json(company_info)
        except Exception as e:
            st.warning(f"기업 정보를 가져오는 중 오류: {e}")

if __name__ == "__main__":
    enhanced_stock_search_main()
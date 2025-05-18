

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# 모듈 임포트
from auth import firebase_auth
from data_fetcher import fetch_dart_financial_data, fetch_stock_price_data, fetch_company_info, get_krx_stock_list
from financial_analysis import calculate_financial_ratios
from technical_analysis import calculate_technical_indicators
from interpret import interpret_financials, interpret_technicals
from visualization import plot_financial_summary, plot_candlestick_with_indicators
from db_handler import save_user_search, get_user_history, get_user_setting, save_user_setting
from utils import get_logger

logger = get_logger(__name__)

# Streamlit 페이지 설정
st.set_page_config(page_title="국내 주식 분석 MVP", layout="wide")

# --- 세션 상태 초기화 ---
if 'krx_stocks_df' not in st.session_state:
    st.session_state.krx_stocks_df = get_krx_stock_list()
    logger.info(f"Loaded KRX stock list into session state. Total: {len(st.session_state.krx_stocks_df)}")

if 'current_stock_code' not in st.session_state:
    # 초기 기본값: 사용자의 최근 검색 기록 또는 삼성전자
    user_id_for_init = firebase_auth.get_current_user_id() # 여기서 user_id를 가져와야 함
    initial_history = get_user_history(user_id_for_init, limit=1)
    st.session_state.current_stock_code = initial_history[0]['stock_code'] if initial_history else "005930"
    logger.info(f"Initialized current_stock_code: {st.session_state.current_stock_code}")

if 'selected_stock_display_name' not in st.session_state:
    st.session_state.selected_stock_display_name = "직접 입력"


# --- 사이드바 ---
st.sidebar.title("🧭 메뉴")

user_id = firebase_auth.get_current_user_id()
if firebase_auth.is_user_logged_in():
    st.sidebar.success(f"로그인됨: {user_id}")
else:
    st.sidebar.warning("로그인이 필요합니다.")

st.sidebar.header("종목 선택")

# KRX 전체 종목 리스트 (종목코드, 종목명)
all_stocks_df = st.session_state.krx_stocks_df

# 1. 기업명 검색 입력
search_term = st.sidebar.text_input(
    "기업명 또는 종목코드 검색",
    placeholder="예: 삼성전자 또는 005930",
    key="search_term_input"
)

# 2. 선택 옵션 생성 (검색 결과 + 최근 조회 + 직접 입력)
options_dict = {"직접 입력": ""}  # {"표시명": "종목코드"}

# 최근 조회 목록 추가 (중복 방지 및 표시명 통일)
search_history = get_user_history(user_id, limit=5)
for item in search_history:
    display_name = f"{item['company_name']} ({item['stock_code']})"
    if display_name not in options_dict and item['stock_code']:
        options_dict[display_name] = item['stock_code']

# 기업명/종목코드 검색 결과 추가
MAX_SEARCH_RESULTS_DISPLAY = 20
if search_term and not all_stocks_df.empty:
    # 'Name'과 'Symbol' 컬럼이 object 타입이고, NaN 값을 가질 수 있으므로 .astype(str) 처리
    name_mask = all_stocks_df['Name'].astype(str).str.contains(search_term, case=False, na=False)
    symbol_mask = all_stocks_df['Symbol'].astype(str).str.contains(search_term, case=False, na=False)
    filtered_df = all_stocks_df[name_mask | symbol_mask]

    count = 0
    for _, row in filtered_df.iterrows():
        display_name = f"{row['Name']} ({row['Symbol']})"
        if display_name not in options_dict and row['Symbol']: # 중복 방지
            options_dict[display_name] = row['Symbol']
            count += 1
            if count >= MAX_SEARCH_RESULTS_DISPLAY:
                st.sidebar.caption(f"검색 결과가 많아 상위 {MAX_SEARCH_RESULTS_DISPLAY}개만 목록에 추가합니다.")
                break
elif not search_term: # 검색어가 없을 때 (초기 상태) "선택하세요"를 맨 위에 추가하고 싶을 수 있음
    # 또는 그냥 최근 조회 목록만 보여줘도 됨
    pass


# Selectbox 표시 순서: 직접 입력 > (검색어 있을 시) 검색 결과 > 최근 조회
# 현재 options_dict는 순서가 보장되지 않으므로, 원하는 순서대로 리스트를 만들어야 함
# 여기서는 간단히 생성된 순서대로 사용
options_list = list(options_dict.keys())

# 현재 선택된 항목이 options_list에 없으면 "직접 입력"으로 설정
current_selection_key = st.session_state.selected_stock_display_name
if current_selection_key not in options_list:
    current_selection_key = "직접 입력"
    st.session_state.selected_stock_display_name = "직접 입력" # 세션 상태도 업데이트

try:
    current_selection_index = options_list.index(current_selection_key)
except ValueError:
    current_selection_index = 0 # "직접 입력"이 기본
    st.session_state.selected_stock_display_name = options_list[0]


selected_display_name = st.sidebar.selectbox(
    "종목 선택",
    options=options_list,
    index=current_selection_index,
    key="stock_selector_unified",
    help="기업명 또는 종목코드를 검색하거나 최근 조회 목록에서 선택하세요. '직접 입력'을 선택하고 아래에 코드를 입력할 수도 있습니다."
)

# selectbox 변경 시 세션 상태 업데이트 및 종목 코드 설정
if st.session_state.selected_stock_display_name != selected_display_name:
    st.session_state.selected_stock_display_name = selected_display_name
    if selected_display_name != "직접 입력":
        st.session_state.current_stock_code = options_dict.get(selected_display_name, st.session_state.current_stock_code)
    # "직접 입력"이 선택되면 current_stock_code는 text_input에서 관리되므로 여기서 변경하지 않음


# 3. 최종 종목 코드 입력 필드
stock_code = st.sidebar.text_input(
    "종목 코드",
    value=st.session_state.current_stock_code,
    placeholder="예: 005930",
    key="stock_code_final_input_unified",
    on_change=lambda: setattr(st.session_state, 'current_stock_code', st.session_state.stock_code_final_input_unified)
).strip()

# text_input 에서 직접 수정했을 경우 current_stock_code 업데이트
if stock_code != st.session_state.current_stock_code:
    st.session_state.current_stock_code = stock_code
    # 만약 사용자가 직접 입력했다면, selectbox 선택을 "직접 입력"으로 변경해주는 것이 자연스러울 수 있음
    if st.session_state.selected_stock_display_name != "직접 입력":
         # 직접 입력시 selectbox를 "직접 입력"으로 바꾸면 사용자 경험이 안좋을 수 있어 주석처리.
         # st.session_state.selected_stock_display_name = "직접 입력"
         # st.experimental_rerun() # Selectbox를 업데이트하기 위해 필요할 수 있음
         pass


# 분석 기간 설정
st.sidebar.header("분석 기간 (기술적 분석)")
default_days_ago = get_user_setting(user_id, "analysis_period_days", 90)
period_options_map = {"3개월": 90, "6개월": 180, "1년": 365, "2년": 730}
default_period_index = 0
if default_days_ago in period_options_map.values():
    default_period_index = list(period_options_map.values()).index(default_days_ago)

selected_period_label = st.sidebar.radio(
    "기간 선택",
    options=list(period_options_map.keys()),
    index=default_period_index,
    key="analysis_period_radio_unified"
)
days_to_subtract = period_options_map[selected_period_label]

if days_to_subtract != default_days_ago:
    save_user_setting(user_id, "analysis_period_days", days_to_subtract)

end_date = datetime.now()
start_date = end_date - timedelta(days=days_to_subtract)

analyze_button = st.sidebar.button("📈 분석 실행", use_container_width=True, key="analyze_button_unified")

# --- 메인 화면 ---
st.title("📊 AI 기반 국내 주식 분석 도구 (MVP)")

if analyze_button and stock_code: # stock_code는 이제 st.session_state.current_stock_code와 동일
    logger.info(f"Analysis started for stock code: {st.session_state.current_stock_code} by user: {user_id}")
    
    with st.spinner("기업 정보 조회 중..."):
        company_info = fetch_company_info(st.session_state.current_stock_code)
        company_name = company_info.get('corp_name', f"종목({st.session_state.current_stock_code})")
        # KRX 리스트에서 회사명 보강
        if (company_name == f"종목({st.session_state.current_stock_code})" or company_name is None) and not all_stocks_df.empty:
            match = all_stocks_df[all_stocks_df['Symbol'] == st.session_state.current_stock_code]
            if not match.empty:
                company_name_krx = match['Name'].iloc[0]
                if company_name_krx:
                    company_name = company_name_krx
                    logger.info(f"Company name updated from KRX list: {company_name}")
                    company_info['corp_name'] = company_name

    st.header(f"분석 결과: {company_name} ({st.session_state.current_stock_code})")
    save_user_search(user_id, st.session_state.current_stock_code, company_name)

    tab1, tab2 = st.tabs(["💰 기업 분석 (재무)", "📈 기술적 분석 (차트)"])

    with tab1:
        st.subheader("재무 분석 및 전략 해석")
        try:
            with st.spinner("DART 재무 데이터 수집 중..."):
                current_year = str(datetime.now().year - 1)
                financial_data_df = fetch_dart_financial_data(st.session_state.current_stock_code, year=current_year)

            if financial_data_df is not None and not financial_data_df.empty:
                with st.spinner("재무 지표 계산 중..."):
                    financial_ratios = calculate_financial_ratios(financial_data_df)
                
                if financial_ratios and "error" not in financial_ratios:
                    st.write("#### 주요 재무 지표")
                    cols = st.columns(3)
                    roe_val = financial_ratios.get('ROE (%)')
                    debt_ratio_val = financial_ratios.get('부채비율 (%)')
                    sales_val = financial_ratios.get('매출액')

                    cols[0].metric("ROE (%)", f"{roe_val:.2f}" if isinstance(roe_val, float) else "N/A")
                    cols[1].metric("부채비율 (%)", f"{debt_ratio_val:.2f}" if isinstance(debt_ratio_val, float) else "N/A")
                    cols[2].metric("매출액", f"{sales_val:,.0f}" if isinstance(sales_val, (int, float)) else "N/A")

                    with st.spinner("재무 요약 차트 생성 중..."):
                        fig_financial_summary = plot_financial_summary(financial_ratios, company_name)
                        st.plotly_chart(fig_financial_summary, use_container_width=True)

                    with st.spinner("전략 해석 메시지 생성 중..."):
                        financial_interpretation = interpret_financials(financial_ratios, company_name)
                        st.info(financial_interpretation)
                else:
                    error_msg = financial_ratios.get('error', '알 수 없는 오류') if isinstance(financial_ratios, dict) else "데이터 포맷 오류"
                    st.error(f"{company_name}의 재무 지표를 계산할 수 없습니다. (데이터 부족 또는 오류: {error_msg})")
            else:
                st.warning(f"{company_name} ({st.session_state.current_stock_code})에 대한 DART 재무 데이터를 가져올 수 없습니다. (지원되지 않는 종목이거나 데이터가 없을 수 있습니다)")
        
        except Exception as e:
            st.error(f"기업 분석 중 오류 발생: {e}")
            logger.error(f"Error in financial analysis pipeline for {st.session_state.current_stock_code}: {e}", exc_info=True)

    with tab2:
        st.subheader("차트 분석 및 단기 시나리오")
        try:
            with st.spinner(f"주가 데이터 수집 중... (기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})"):
                price_data_df = fetch_stock_price_data(st.session_state.current_stock_code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

            if price_data_df is not None and not price_data_df.empty:
                with st.spinner("기술적 지표 계산 중..."):
                    price_df_with_indicators = calculate_technical_indicators(price_data_df.copy())
                
                with st.spinner("캔들 차트 및 지표 시각화 중..."):
                    fig_candlestick = plot_candlestick_with_indicators(price_df_with_indicators, company_name)
                    st.plotly_chart(fig_candlestick, use_container_width=True)

                with st.spinner("단기 시나리오 해석 중..."):
                    technical_interpretation = interpret_technicals(price_df_with_indicators, company_name)
                    st.info(technical_interpretation)
            else:
                st.warning(f"{company_name} ({st.session_state.current_stock_code})에 대한 주가 데이터를 가져올 수 없습니다.")
        
        except Exception as e:
            st.error(f"기술적 분석 중 오류 발생: {e}")
            logger.error(f"Error in technical analysis pipeline for {st.session_state.current_stock_code}: {e}", exc_info=True)

elif analyze_button and not st.session_state.current_stock_code: # stock_code 대신 세션 상태 사용
    st.error("종목 코드를 입력하거나 선택해주세요.")
else:
    st.info("좌측 사이드바에서 분석할 종목을 검색, 선택하거나 코드를 직접 입력하고 '분석 실행' 버튼을 클릭하세요.")

st.sidebar.markdown("---")
st.sidebar.markdown("제작: 스켈터랩스")
st.sidebar.markdown("Ver 0.3 (MVP)")
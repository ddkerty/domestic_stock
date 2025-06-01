import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# --- 기존 모듈 임포트 ---
from auth import firebase_auth
from data_fetcher import (
    fetch_dart_financial_data,
    fetch_stock_price_data,
    fetch_company_info,
    get_krx_stock_list,
)
from financial_analysis import calculate_financial_ratios
from technical_analysis import calculate_technical_indicators
from interpret import interpret_financials, interpret_technicals
from visualization import plot_financial_summary, plot_candlestick_with_indicators
from db_handler import save_user_search, get_user_history, get_user_setting, save_user_setting
from utils import get_logger

# --- 새로 추가된 모듈 임포트 ---
from enhanced_search import stock_search_selectbox, stock_search_dynamic, stock_search_advanced


logger = get_logger(__name__)

st.set_page_config(page_title="국내 주식 분석 MVP", layout="wide")

# --- 세션 상태 초기화 ---
# KRX 주식 목록 로드
if 'krx_stocks_df' not in st.session_state:
    st.session_state.krx_stocks_df = get_krx_stock_list()
    if st.session_state.krx_stocks_df.empty:
        logger.warning("KRX stock list is empty after loading!")
    else:
        logger.info(f"Loaded KRX stock list into session state. Total: {len(st.session_state.krx_stocks_df)}")

# 현재 선택된 종목 코드 초기화 (최근 기록 또는 기본값)
if 'current_stock_code' not in st.session_state:
    user_id_for_init = firebase_auth.get_current_user_id()
    initial_history = get_user_history(user_id_for_init, limit=1)
    st.session_state.current_stock_code = initial_history[0]['stock_code'] if initial_history else "005930" # 기본값: 삼성전자
    logger.info(f"Initialized current_stock_code: {st.session_state.current_stock_code}")

# --- 사이드바 ---
st.sidebar.title("🧭 메뉴")
user_id = firebase_auth.get_current_user_id()
if firebase_auth.is_user_logged_in():
    st.sidebar.success(f"로그인됨: {user_id}")
else:
    st.sidebar.warning("로그인이 필요합니다.")

st.sidebar.header("종목 선택")

# --- START: 개선된 검색 기능 통합 ---
# 검색 방법 선택 라디오 버튼
search_method = st.sidebar.radio(
    "검색 방법 선택",
    ["기본 검색", "동적 검색", "고급 검색"],
    index=1,  # '동적 검색'을 기본으로 설정
    help="""
    **기본 검색**: 간단한 드롭다운 메뉴 방식입니다.
    **동적 검색**: 입력과 동시에 실시간으로 검색 결과가 표시됩니다.
    **고급 검색**: 자동완성 기능이 포함된 전문적인 검색 방식입니다. (streamlit-searchbox 필요)
    """
)

# 선택된 방법에 따라 다른 검색 인터페이스 표시
selected_stock_code = None

# st.sidebar 공간에서 검색 UI를 직접 실행
with st.sidebar:
    if search_method == "기본 검색":
        selected_stock_code = stock_search_selectbox()
    elif search_method == "동적 검색":
        selected_stock_code = stock_search_dynamic()
    elif search_method == "고급 검색":
        selected_stock_code = stock_search_advanced()

# 검색 컴포넌트에서 새로운 종목 코드가 반환되면 세션 상태 업데이트
if selected_stock_code:
    st.session_state.current_stock_code = selected_stock_code
# --- END: 개선된 검색 기능 통합 ---

st.sidebar.markdown("---")

# --- 최근 조회 기록 (기존 로직 유지) ---
st.sidebar.header("최근 조회 기록")
search_history = get_user_history(user_id, limit=3)
if not search_history:
    st.sidebar.caption("최근 조회 기록이 없습니다.")
for idx, item in enumerate(search_history):
    stock_code = item.get("stock_code", "UNKNOWN")
    corp_name = item.get("corp_name", f"기업({stock_code})")
    if st.sidebar.button(corp_name, key=f"history_{stock_code}_{idx}", use_container_width=True, type="secondary"):
        st.session_state.current_stock_code = stock_code
        # 동적/고급 검색의 선택 상태를 초기화할 필요가 있을 수 있음
        if 'selected_stock' in st.session_state:
            del st.session_state['selected_stock']
        st.rerun()

# --- 분석 기간 설정 및 분석 실행 버튼 (기존 로직 유지) ---
st.sidebar.header("분석 기간 (기술적 분석)")
default_days_ago = get_user_setting(user_id, "analysis_period_days", 90)
period_options_map = {"3개월": 90, "6개월": 180, "1년": 365, "2년": 730}
default_period_index = list(period_options_map.values()).index(default_days_ago) if default_days_ago in period_options_map.values() else 0

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

analyze_button = st.sidebar.button("📊 분석 실행", use_container_width=True, key="analyze_button_unified", type="primary")

# --- 메인 화면 ---
final_stock_code_to_analyze = st.session_state.current_stock_code

st.title("📈 AI 기반 국내 주식 분석 도구 (MVP)")

if analyze_button and final_stock_code_to_analyze:
    logger.info(f"Analysis started for stock code: {final_stock_code_to_analyze} by user: {user_id}")

    with st.spinner("기업 정보 조회 중..."):
        company_info = fetch_company_info(final_stock_code_to_analyze)
        company_name = company_info.get('corp_name', f"종목({final_stock_code_to_analyze})")

    st.header(f"분석 결과: {company_name} ({final_stock_code_to_analyze})")
    save_user_search(user_id, final_stock_code_to_analyze, company_name)

    tab1, tab2 = st.tabs(["💰 기업 분석 (재무)", "📈 기술적 분석 (차트)"])

    with tab1:
        st.subheader("재무 분석 및 해석")
        try:
            with st.spinner("DART 재무 데이터 수집 중..."):
                now = datetime.now()
                # 5월 이전에는 전전년도 재무제표가 최신일 수 있음
                current_year = str(now.year - 1 if now.month >= 5 else now.year - 2)
                financial_data_df = fetch_dart_financial_data(
                    final_stock_code_to_analyze,
                    year=current_year,
                    report_code="11011" # 11011: 사업보고서 (정기)
                )
            if financial_data_df is not None and not financial_data_df.empty:
                financial_ratios = calculate_financial_ratios(financial_data_df)
                if financial_ratios and "error" not in financial_ratios:
                    cols = st.columns(3)
                    cols[0].metric("ROE (%)", f"{financial_ratios.get('ROE (%)', 0):.2f}" if pd.notna(financial_ratios.get('ROE (%)')) else "N/A")
                    cols[1].metric("부채비율 (%)", f"{financial_ratios.get('부채비율 (%)', 0):.2f}" if pd.notna(financial_ratios.get('부채비율 (%)')) else "N/A")
                    sales_value = financial_ratios.get('매출액')
                    cols[2].metric("매출액 (억원)", f"{sales_value / 100000000:,.0f}" if pd.notna(sales_value) else "N/A")
                    
                    st.plotly_chart(plot_financial_summary(financial_ratios, company_name), use_container_width=True)
                    st.info(interpret_financials(financial_ratios, company_name))
                else:
                    st.error("재무 지표를 계산하는데 실패했습니다. 데이터가 부족할 수 있습니다.")
            else:
                st.warning("DART에서 해당 기간의 재무 데이터를 가져올 수 없습니다. 비상장 주식이거나 데이터가 없는 종목일 수 있습니다.")
        except Exception as e:
            st.error(f"기업 분석 중 오류 발생: {e}")
            logger.error(f"Error in financial analysis pipeline: {e}", exc_info=True)

    with tab2:
        st.subheader("차트 분석 및 기술적 지표 해석")
        try:
            with st.spinner(f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} 기간의 주가 데이터 수집 중..."):
                price_data_df = fetch_stock_price_data(final_stock_code_to_analyze, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            if price_data_df is not None and not price_data_df.empty:
                price_df_with_indicators = calculate_technical_indicators(price_data_df.copy())
                st.plotly_chart(plot_candlestick_with_indicators(price_df_with_indicators, company_name), use_container_width=True)
                st.info(interpret_technicals(price_df_with_indicators, company_name))
            else:
                st.warning("주가 데이터를 가져올 수 없습니다. 종목 코드를 확인하거나 기간을 다시 설정해보세요.")
        except Exception as e:
            st.error(f"기술적 분석 중 오류 발생: {e}")
            logger.error(f"Error in technical analysis pipeline: {e}", exc_info=True)

elif analyze_button and not final_stock_code_to_analyze:
    st.error("먼저 종목을 선택해주세요.")
else:
    st.info("👈 사이드바에서 종목을 선택한 후 '분석 실행' 버튼을 클릭하세요.")

st.sidebar.markdown("---")
st.sidebar.info("문의: Gemini AI Solutions")
st.sidebar.markdown("Ver 0.7 (Search Enhanced)")
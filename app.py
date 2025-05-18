import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

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

logger = get_logger(__name__)

st.set_page_config(page_title="국내 주식 분석 MVP", layout="wide")

if 'krx_stocks_df' not in st.session_state:
    st.session_state.krx_stocks_df = get_krx_stock_list()
    if st.session_state.krx_stocks_df.empty:
        logger.warning("KRX stock list is empty after loading!")
    else:
        logger.info(f"Loaded KRX stock list into session state. Total: {len(st.session_state.krx_stocks_df)}")

if 'current_stock_code' not in st.session_state:
    user_id_for_init = firebase_auth.get_current_user_id()
    initial_history = get_user_history(user_id_for_init, limit=1)
    st.session_state.current_stock_code = initial_history[0]['stock_code'] if initial_history else "005930"
    logger.info(f"Initialized current_stock_code: {st.session_state.current_stock_code}")

if 'search_input_value' not in st.session_state:
    temp_df = st.session_state.get('krx_stocks_df', pd.DataFrame())
    if not temp_df.empty:
        match = temp_df[temp_df['Symbol'] == st.session_state.current_stock_code]
        if not match.empty:
            st.session_state.search_input_value = f"{match['Name'].iloc[0]} ({st.session_state.current_stock_code})"
        else:
            st.session_state.search_input_value = st.session_state.current_stock_code
    else:
        st.session_state.search_input_value = st.session_state.current_stock_code

if 'show_search_results' not in st.session_state:
    st.session_state.show_search_results = False
if 'filtered_search_results' not in st.session_state:
    st.session_state.filtered_search_results = pd.DataFrame()

st.sidebar.title("🧭 메뉴")
user_id = firebase_auth.get_current_user_id()
if firebase_auth.is_user_logged_in():
    st.sidebar.success(f"로그인됨: {user_id}")
else:
    st.sidebar.warning("로그인이 필요합니다.")

st.sidebar.header("종목 선택")
all_stocks_df = st.session_state.krx_stocks_df

def search_input_changed():
    current_input = st.session_state.stock_search_input_key
    st.session_state.search_input_value = current_input

    if current_input and len(current_input) >= 1:
        if not all_stocks_df.empty:
            name_to_search = current_input.split(' (')[0]
            name_mask = all_stocks_df['Name'].astype(str).str.contains(name_to_search, case=False, na=False)
            symbol_mask = all_stocks_df['Symbol'].astype(str).str.startswith(current_input)
            filtered_df = all_stocks_df[name_mask | symbol_mask].copy()
            if not filtered_df.empty:
                filtered_df['display_name'] = filtered_df['Name'] + " (" + filtered_df['Symbol'] + ")"
            st.session_state.filtered_search_results = filtered_df
            st.session_state.show_search_results = True
        else:
            st.session_state.filtered_search_results = pd.DataFrame()
            st.session_state.show_search_results = False

search_input_widget = st.sidebar.text_input(
    "기업명 또는 종목코드 검색/입력",
    value=st.session_state.search_input_value,
    on_change=search_input_changed,
    key="stock_search_input_key",
    placeholder="예: 삼성 또는 005930",
)

if st.session_state.show_search_results and not st.session_state.filtered_search_results.empty:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**검색 결과:**")
    results_df = st.session_state.filtered_search_results
    MAX_DISPLAY_RESULTS = 7

    def select_searched_item(selected_symbol, selected_display_name):
        st.session_state.current_stock_code = selected_symbol
        st.session_state.search_input_value = selected_display_name
        st.session_state.show_search_results = False

    for i, row_tuple in enumerate(results_df.head(MAX_DISPLAY_RESULTS).itertuples()):
        if st.sidebar.button(f"{row_tuple.display_name}", key=f"search_result_{row_tuple.Symbol}", use_container_width=True):
            select_searched_item(row_tuple.Symbol, row_tuple.display_name)
            st.rerun()

    if len(results_df) > MAX_DISPLAY_RESULTS:
        st.sidebar.caption(f"... 외 {len(results_df) - MAX_DISPLAY_RESULTS}개 더 있음")
    st.sidebar.markdown("---")

search_history = get_user_history(user_id, limit=3)
if not search_history:
    st.sidebar.caption("최근 조회 기록이 없습니다.")
for idx, item in enumerate(search_history):
    stock_code = item.get("stock_code", "UNKNOWN")
    corp_name = item.get("corp_name", f"기업({stock_code})")
    if st.sidebar.button(corp_name, key=f"history_{stock_code}_{idx}", use_container_width=True, type="secondary"):
        st.session_state.current_stock_code = stock_code
        st.session_state.search_input_value = corp_name
        st.session_state.show_search_results = False
        st.rerun()

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

analyze_button = st.sidebar.button("\U0001F4C8 분석 실행", use_container_width=True, key="analyze_button_unified")

if analyze_button:
    user_input = st.session_state.get("stock_search_input_key", "").strip()
    if user_input.isdigit() and len(user_input) == 6:
        logger.info(f"직접 입력된 종목코드 감지: {user_input}")
        st.session_state.current_stock_code = user_input
        if not st.session_state.krx_stocks_df.empty:
            if not st.session_state.krx_stocks_df['Symbol'].isin([user_input]).any():
                st.warning(f"입력한 종목코드 '{user_input}'는 KRX 목록에 존재하지 않습니다. 분석을 시도하지만, 기업명이 정확하지 않을 수 있습니다.")
        else:
            logger.warning("KRX 주식 목록을 불러오지 못해 종목코드 유효성 검사를 생략합니다.")

final_stock_code_to_analyze = st.session_state.current_stock_code

st.title("\U0001F4CA AI 기반 국내 주식 분석 도구 (MVP)")

if analyze_button and final_stock_code_to_analyze:
    logger.info(f"Analysis started for stock code: {final_stock_code_to_analyze} by user: {user_id}")

    with st.spinner("기업 정보 조회 중..."):
        company_info = fetch_company_info(final_stock_code_to_analyze)
        company_name = company_info.get('corp_name', f"종목({final_stock_code_to_analyze})")

    st.header(f"분석 결과: {company_name} ({final_stock_code_to_analyze})")
    save_user_search(user_id, final_stock_code_to_analyze, company_name)

    tab1, tab2 = st.tabs(["\U0001F4B0 기업 분석 (재무)", "\U0001F4C8 기술적 분석 (차트)"])

    with tab1:
        st.subheader("재무 분석 및 전략 해석")
        try:
            with st.spinner("DART 재무 데이터 수집 중..."):
                now = datetime.now()
                current_year = str(now.year - 1 if now.month >= 5 else now.year - 2)
                financial_data_df = fetch_dart_financial_data(
                    final_stock_code_to_analyze,
                    year=current_year,
                    report_code="11014"
                )
            if financial_data_df is not None and not financial_data_df.empty:
                financial_ratios = calculate_financial_ratios(financial_data_df)
                if financial_ratios and "error" not in financial_ratios:
                    cols = st.columns(3)
                    cols[0].metric("ROE (%)", f"{financial_ratios.get('ROE (%)', 'N/A'):.2f}" if pd.notna(financial_ratios.get('ROE (%)')) else "N/A")
                    cols[1].metric("부채비율 (%)", f"{financial_ratios.get('부채비율 (%)', 'N/A'):.2f}" if pd.notna(financial_ratios.get('부채비율 (%)')) else "N/A")
                    cols[2].metric("매출액", f"{financial_ratios.get('매출액', 'N/A'):,.0f}" if pd.notna(financial_ratios.get('매출액')) else "N/A")
                    st.plotly_chart(plot_financial_summary(financial_ratios, company_name), use_container_width=True)
                    st.info(interpret_financials(financial_ratios, company_name))
                else:
                    st.error("재무 지표 계산 실패")
            else:
                st.warning("DART 재무 데이터를 가져올 수 없습니다.")
        except Exception as e:
            st.error(f"기업 분석 중 오류 발생: {e}")
            logger.error(f"Error in financial analysis pipeline: {e}", exc_info=True)

    with tab2:
        st.subheader("차트 분석 및 단기 시나리오")
        try:
            price_data_df = fetch_stock_price_data(final_stock_code_to_analyze, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            if price_data_df is not None and not price_data_df.empty:
                price_df_with_indicators = calculate_technical_indicators(price_data_df.copy())
                st.plotly_chart(plot_candlestick_with_indicators(price_df_with_indicators, company_name), use_container_width=True)
                st.info(interpret_technicals(price_df_with_indicators, company_name))
            else:
                st.warning("주가 데이터를 가져올 수 없습니다.")
        except Exception as e:
            st.error(f"기술적 분석 중 오류 발생: {e}")
            logger.error(f"Error in technical analysis pipeline: {e}", exc_info=True)

elif analyze_button and not final_stock_code_to_analyze:
    st.error("종목 코드를 입력하거나 선택해주세요.")
else:
    st.info("좌측 사이드바에서 종목을 검색하거나 직접 종목코드를 입력한 후 '분석 실행'을 클릭하세요.")

st.sidebar.markdown("---")
st.sidebar.markdown("제작: 스켈터랩스")
st.sidebar.markdown("Ver 0.6 (MVP)")

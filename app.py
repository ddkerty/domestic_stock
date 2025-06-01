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

# --- UX 개선을 위해 단일 검색 함수만 임포트 ---
from enhanced_search import unified_stock_search


logger = get_logger(__name__)

st.set_page_config(page_title="국내 주식 분석 MVP", layout="wide")

# --- 세션 상태 초기화 ---
if 'krx_stocks_df' not in st.session_state:
    st.session_state.krx_stocks_df = get_krx_stock_list()
    if st.session_state.krx_stocks_df.empty:
        logger.warning("KRX stock list is empty after loading!")
    else:
        logger.info(f"Loaded KRX stock list. Total: {len(st.session_state.krx_stocks_df)}")

if 'current_stock_code' not in st.session_state:
    user_id_for_init = firebase_auth.get_current_user_id()
    initial_history = get_user_history(user_id_for_init, limit=1)
    st.session_state.current_stock_code = initial_history[0]['stock_code'] if initial_history else "005930"
    logger.info(f"Initialized current_stock_code: {st.session_state.current_stock_code}")

# --- 사이드바 ---
st.sidebar.title("🧭 메뉴")
user_id = firebase_auth.get_current_user_id()
if firebase_auth.is_user_logged_in():
    st.sidebar.success(f"로그인됨: {user_id}")
else:
    st.sidebar.warning("로그인이 필요합니다.")

st.sidebar.header("종목 선택")

with st.sidebar:
    selected_stock_code = unified_stock_search()

if selected_stock_code and selected_stock_code != st.session_state.get('current_stock_code'):
    st.session_state.current_stock_code = selected_stock_code
    st.rerun()

st.sidebar.markdown("---")

# --- 최근 조회 기록 ---
st.sidebar.header("최근 조회 기록")
search_history = get_user_history(user_id, limit=3)
if not search_history:
    st.sidebar.caption("최근 조회 기록이 없습니다.")
for idx, item in enumerate(search_history):
    stock_code = item.get("stock_code", "UNKNOWN")
    corp_name = item.get("corp_name", f"기업({stock_code})")
    if st.sidebar.button(corp_name, key=f"history_{stock_code}_{idx}", use_container_width=True, type="secondary"):
        st.session_state.current_stock_code = stock_code
        st.rerun()

# --- 분석 기간 설정 및 분석 실행 버튼 ---
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

try:
    all_stocks = st.session_state.krx_stocks_df
    if not all_stocks.empty:
        current_stock_name = all_stocks[all_stocks['Symbol'] == final_stock_code_to_analyze]['Name'].iloc[0]
        st.title(f"📈 {current_stock_name} ({final_stock_code_to_analyze})")
    else:
        st.title(f"📈 AI 기반 국내 주식 분석")
        if final_stock_code_to_analyze:
             st.warning(f"{final_stock_code_to_analyze} 종목 정보를 찾을 수 없습니다. 목록을 불러오는 중일 수 있습니다.")
except (IndexError, KeyError, TypeError):
    st.title(f"📈 AI 기반 국내 주식 분석")
    if final_stock_code_to_analyze:
        st.warning(f"{final_stock_code_to_analyze} 종목 정보를 찾을 수 없습니다. 목록을 불러오는 중일 수 있습니다.")


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
                current_year = str(now.year - 1 if now.month >= 5 else now.year - 2)
                
                # --- START: 수정된 부분 ---
                # fetch_dart_financial_data는 이제 (데이터프레임, 메시지) 튜플을 반환
                # 튜플을 df와 msg 두 변수로 올바르게 풀어줍니다.
                df, msg = fetch_dart_financial_data(
                    final_stock_code_to_analyze,
                    year=current_year,
                    report_code="11011"
                )
            
            # 튜플로 받은 변수 중 데이터프레임(df)에 대해서만 .empty를 확인합니다.
            if not df.empty:
                financial_ratios = calculate_financial_ratios(df)
                if financial_ratios and "error" not in financial_ratios:
                    cols = st.columns(3)
                    cols[0].metric("ROE (%)", f"{financial_ratios.get('ROE (%)', 0):.2f}" if pd.notna(financial_ratios.get('ROE (%)')) else "N/A")
                    cols[1].metric("부채비율 (%)", f"{financial_ratios.get('부채비율 (%)', 0):.2f}" if pd.notna(financial_ratios.get('부채비율 (%)')) else "N/A")
                    sales_value = financial_ratios.get('매출액')
                    cols[2].metric("매출액 (억원)", f"{sales_value / 100000000:,.0f}" if pd.notna(sales_value) else "N/A")
                    
                    st.plotly_chart(plot_financial_summary(financial_ratios, company_name), use_container_width=True)
                    st.info(interpret_financials(financial_ratios, company_name))
                else:
                    st.error("재무 지표를 계산하는데 실패했습니다.")
            else:
                # 데이터가 없을 경우, 함께 반환된 상세 메시지(msg)를 표시합니다.
                st.warning(msg)
            # --- END: 수정된 부분 ---

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
                st.warning("주가 데이터를 가져올 수 없습니다.")
        except Exception as e:
            st.error(f"기술적 분석 중 오류 발생: {e}")
            logger.error(f"Error in technical analysis pipeline: {e}", exc_info=True)

elif analyze_button and not final_stock_code_to_analyze:
    st.error("먼저 종목을 선택해주세요.")
else:
    st.info("👈 사이드바에서 분석할 종목을 선택한 후 '분석 실행' 버튼을 클릭하세요.")

st.sidebar.markdown("---")
st.sidebar.info("문의: Gemini AI Solutions")
st.sidebar.markdown("Ver 1.0 (Stable)")
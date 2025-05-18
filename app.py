

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd # pandas 임포트 추가

# 모듈 임포트 (프로젝트 구조에 맞게)
from auth import firebase_auth
from data_fetcher import fetch_dart_financial_data, fetch_stock_price_data, fetch_company_info, get_krx_stock_list # get_krx_stock_list 추가
from financial_analysis import calculate_financial_ratios
from technical_analysis import calculate_technical_indicators
from interpret import interpret_financials, interpret_technicals # interpret.py 에 pandas 임포트 확인 필요
from visualization import plot_financial_summary, plot_candlestick_with_indicators
from db_handler import save_user_search, get_user_history, get_user_setting, save_user_setting
from utils import get_logger

logger = get_logger(__name__)

# Streamlit 페이지 설정
st.set_page_config(page_title="국내 주식 분석 MVP", layout="wide")

# --- 사이드바 ---
st.sidebar.title("🧭 메뉴")

# 사용자 인증 (MVP에서는 mock)
user_id = firebase_auth.get_current_user_id()
if firebase_auth.is_user_logged_in():
    st.sidebar.success(f"로그인됨: {user_id}")
else:
    st.sidebar.warning("로그인이 필요합니다.")

st.sidebar.header("종목 선택")

# 1. 기업명 검색 기능
st.sidebar.subheader("1. 기업명으로 검색")
# 세션 상태에 KRX 종목 리스트 저장 (앱 로드 시 한 번만 호출)
if 'krx_stocks_df' not in st.session_state:
    st.session_state.krx_stocks_df = get_krx_stock_list()
all_stocks_df = st.session_state.krx_stocks_df


search_term = st.sidebar.text_input("기업명 일부를 입력하세요 (예: 삼성)", key="company_search_term")

filtered_stocks_options = {"선택하세요...": ""} # Selectbox 옵션용 딕셔너리: "표시명": "종목코드"
if search_term and not all_stocks_df.empty:
    # 'Name' 컬럼이 object 타입이고, NaN 값을 가질 수 있으므로 .astype(str) 처리
    mask = all_stocks_df['Name'].astype(str).str.contains(search_term, case=False, na=False)
    filtered_df = all_stocks_df[mask]
    for _, row in filtered_df.iterrows():
        display_name = f"{row['Name']} ({row['Symbol']})"
        filtered_stocks_options[display_name] = row['Symbol']

# 검색 결과가 많을 경우를 대비해 표시 개수 제한 (예: 상위 20개)
MAX_SEARCH_RESULTS = 20
options_to_display = list(filtered_stocks_options.keys())
if len(options_to_display) > MAX_SEARCH_RESULTS + 1 : # "+1" for "선택하세요..."
    options_to_display = options_to_display[:MAX_SEARCH_RESULTS + 1]
    st.sidebar.caption(f"검색 결과가 너무 많습니다. 상위 {MAX_SEARCH_RESULTS}개만 표시됩니다.")


selected_company_display_name = st.sidebar.selectbox(
    "검색된 기업 선택",
    options=options_to_display,
    key="company_selectbox"
)

# 2. 최근 조회 종목 또는 직접 입력
st.sidebar.subheader("2. 최근 조회 또는 직접 입력")
search_history = get_user_history(user_id, limit=5)
# 최근 조회 종목 옵션: "표시명": "종목코드"
history_options = {"직접 입력": ""} # 기본 옵션
for h in search_history:
    if h['company_name'] and h['stock_code']:
        history_options[f"{h['company_name']} ({h['stock_code']})"] = h['stock_code']

selected_history_key = st.sidebar.selectbox(
    "최근 조회 / 직접 입력",
    options=list(history_options.keys()),
    key="history_selectbox"
)

# 종목 코드 결정 로직
# 세션 상태를 사용하여 종목 코드 값을 유지하고 업데이트
if 'current_stock_code' not in st.session_state:
    st.session_state.current_stock_code = search_history[0]['stock_code'] if search_history else "005930" # 초기 기본값

# 기업명 검색 결과에 따라 종목 코드 업데이트
if selected_company_display_name != "선택하세요...":
    st.session_state.current_stock_code = filtered_stocks_options.get(selected_company_display_name, st.session_state.current_stock_code)
# 최근 조회/직접 입력 선택에 따라 종목 코드 업데이트 (기업명 검색이 우선)
elif selected_history_key != "직접 입력":
     st.session_state.current_stock_code = history_options.get(selected_history_key, st.session_state.current_stock_code)
elif selected_history_key == "직접 입력" and selected_company_display_name == "선택하세요...": # 사용자가 명시적으로 직접 입력을 선택한 경우
    pass # current_stock_code는 이전 값을 유지하거나 아래 text_input에서 변경됨

stock_code = st.sidebar.text_input(
    "종목 코드",
    value=st.session_state.current_stock_code, # 세션 상태 값 사용
    placeholder="예: 005930",
    key="stock_code_final_input",
    on_change=lambda: setattr(st.session_state, 'current_stock_code', st.session_state.stock_code_final_input) # 입력 변경 시 세션 업데이트
).strip()
# 사용자가 직접 입력하면 current_stock_code가 업데이트됨
if stock_code != st.session_state.current_stock_code : # text_input이 변경된 경우
     st.session_state.current_stock_code = stock_code


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
    key="analysis_period_radio"
)
days_to_subtract = period_options_map[selected_period_label]

if days_to_subtract != default_days_ago:
    save_user_setting(user_id, "analysis_period_days", days_to_subtract)

end_date = datetime.now()
start_date = end_date - timedelta(days=days_to_subtract)

analyze_button = st.sidebar.button("📈 분석 실행", use_container_width=True, key="analyze_button")

# --- 메인 화면 ---
st.title("📊 AI 기반 국내 주식 분석 도구 (MVP)")

if analyze_button and stock_code:
    logger.info(f"Analysis started for stock code: {stock_code} by user: {user_id}")
    
    with st.spinner("기업 정보 조회 중..."):
        company_info = fetch_company_info(stock_code)
        company_name = company_info.get('corp_name', f"종목({stock_code})")
        # KRX 리스트에서 회사명 보강
        if (company_name == f"종목({stock_code})" or company_name is None) and not all_stocks_df.empty:
            match = all_stocks_df[all_stocks_df['Symbol'] == stock_code]
            if not match.empty:
                company_name_krx = match['Name'].iloc[0]
                if company_name_krx: # KRX에서 유효한 이름을 가져왔다면
                    company_name = company_name_krx
                    logger.info(f"Company name updated from KRX list: {company_name}")
                    company_info['corp_name'] = company_name # company_info도 업데이트

    st.header(f"분석 결과: {company_name} ({stock_code})")
    save_user_search(user_id, stock_code, company_name)

    tab1, tab2 = st.tabs(["💰 기업 분석 (재무)", "📈 기술적 분석 (차트)"])

    with tab1:
        st.subheader("재무 분석 및 전략 해석")
        try:
            with st.spinner("DART 재무 데이터 수집 중..."):
                current_year = str(datetime.now().year - 1)
                financial_data_df = fetch_dart_financial_data(stock_code, year=current_year)

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
                st.warning(f"{company_name} ({stock_code})에 대한 DART 재무 데이터를 가져올 수 없습니다. (지원되지 않는 종목이거나 데이터가 없을 수 있습니다)")
        
        except Exception as e:
            st.error(f"기업 분석 중 오류 발생: {e}")
            logger.error(f"Error in financial analysis pipeline for {stock_code}: {e}", exc_info=True)

    with tab2:
        st.subheader("차트 분석 및 단기 시나리오")
        try:
            with st.spinner(f"주가 데이터 수집 중... (기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})"):
                price_data_df = fetch_stock_price_data(stock_code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

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
                st.warning(f"{company_name} ({stock_code})에 대한 주가 데이터를 가져올 수 없습니다.")
        
        except Exception as e:
            st.error(f"기술적 분석 중 오류 발생: {e}")
            logger.error(f"Error in technical analysis pipeline for {stock_code}: {e}", exc_info=True)

elif analyze_button and not stock_code:
    st.error("종목 코드를 입력해주세요.")
else:
    st.info("좌측 사이드바에서 분석할 종목을 선택하거나 코드를 입력하고 '분석 실행' 버튼을 클릭하세요.")

st.sidebar.markdown("---")
st.sidebar.markdown("제작: 스켈터랩스")
st.sidebar.markdown("Ver 0.2 (MVP)")

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
    user_id_for_init = firebase_auth.get_current_user_id()
    initial_history = get_user_history(user_id_for_init, limit=1)
    st.session_state.current_stock_code = initial_history[0]['stock_code'] if initial_history else "005930"
    logger.info(f"Initialized current_stock_code: {st.session_state.current_stock_code}")

if 'search_input_value' not in st.session_state:
    # 초기 검색창 값: current_stock_code에 해당하는 기업명 + 코드 또는 코드만
    # 여기서는 간단히 코드로 시작, 필요시 기업명으로 초기화 로직 추가
    st.session_state.search_input_value = st.session_state.current_stock_code

if 'show_search_results' not in st.session_state:
    st.session_state.show_search_results = False # 검색 결과 표시 여부

if 'filtered_search_results' not in st.session_state:
    st.session_state.filtered_search_results = pd.DataFrame() # 검색 결과 저장

# --- 사이드바 ---
st.sidebar.title("🧭 메뉴")

user_id = firebase_auth.get_current_user_id()
if firebase_auth.is_user_logged_in():
    st.sidebar.success(f"로그인됨: {user_id}")
else:
    st.sidebar.warning("로그인이 필요합니다.")

st.sidebar.header("종목 선택")

all_stocks_df = st.session_state.krx_stocks_df

# 검색어 입력 콜백
def search_input_changed():
    current_input = st.session_state.stock_search_input_key
    st.session_state.search_input_value = current_input # 현재 입력값을 세션에 저장

    if current_input and len(current_input) > 1 : # 최소 2글자 이상 입력 시 검색 시작 (너무 잦은 검색 방지)
        if not all_stocks_df.empty:
            # 기업명 또는 종목코드로 검색
            name_mask = all_stocks_df['Name'].astype(str).str.contains(current_input, case=False, na=False)
            symbol_mask = all_stocks_df['Symbol'].astype(str).str.startswith(current_input) # 코드는 시작부분 일치로
            
            filtered_df = all_stocks_df[name_mask | symbol_mask].copy() # .copy() 추가
            
            # 검색 결과에 표시할 이름 생성 ('Name (Symbol)')
            if not filtered_df.empty:
                filtered_df['display_name'] = filtered_df['Name'] + " (" + filtered_df['Symbol'] + ")"
            
            st.session_state.filtered_search_results = filtered_df
            st.session_state.show_search_results = True
            logger.info(f"Search for '{current_input}', found {len(filtered_df)} results.")
        else:
            st.session_state.show_search_results = False
            st.session_state.filtered_search_results = pd.DataFrame()
    else: # 입력이 짧거나 없으면 결과 숨김
        st.session_state.show_search_results = False
        st.session_state.filtered_search_results = pd.DataFrame()

# 1. 통합 검색/입력 창
search_input = st.sidebar.text_input(
    "기업명 또는 종목코드 검색/입력",
    value=st.session_state.search_input_value, # 세션 값 사용
    on_change=search_input_changed, # 입력 변경 시 콜백
    key="stock_search_input_key",
    placeholder="예: 삼성 또는 005930",
    help="기업명(2글자 이상) 또는 종목코드를 입력하세요."
)

# 2. 검색 결과 드롭다운 (버튼 또는 라디오 형태로 표시)
if st.session_state.show_search_results and not st.session_state.filtered_search_results.empty:
    st.sidebar.markdown("---") # 구분선
    st.sidebar.markdown("**검색 결과:**")
    
    results_df = st.session_state.filtered_search_results
    MAX_DISPLAY_RESULTS = 7 # 표시할 최대 결과 수
    
    # 사용자가 결과를 클릭했을 때의 콜백
    def select_searched_item(selected_symbol, selected_display_name):
        st.session_state.current_stock_code = selected_symbol
        st.session_state.search_input_value = selected_display_name # 검색창에 선택된 항목 표시
        st.session_state.show_search_results = False # 결과 목록 숨김
        logger.info(f"Item selected from search: {selected_display_name}, Code: {selected_symbol}")
        # 입력창 업데이트를 위해 rerun이 필요할 수 있으나, Streamlit이 자동으로 처리할 가능성 높음

    for i, row in enumerate(results_df.head(MAX_DISPLAY_RESULTS).itertuples()):
        # 각 결과를 버튼으로 만듦
        if st.sidebar.button(f"{row.display_name}", key=f"search_result_{row.Symbol}", use_container_width=True):
            select_searched_item(row.Symbol, row.display_name)
            st.rerun() # 버튼 클릭 후 즉시 반영 및 목록 숨기기 위해

    if len(results_df) > MAX_DISPLAY_RESULTS:
        st.sidebar.caption(f"... 외 {len(results_df) - MAX_DISPLAY_RESULTS}개 더 있음")
    st.sidebar.markdown("---")


# 3. 최근 조회 목록 (선택 사항)
st.sidebar.markdown("**최근 조회:**")
search_history = get_user_history(user_id, limit=3)
if not search_history:
    st.sidebar.caption("최근 조회 기록이 없습니다.")

for item in search_history:
    history_display_name = f"{item['company_name']} ({item['stock_code']})"
    if st.sidebar.button(history_display_name, key=f"history_{item['stock_code']}", use_container_width=True, type="secondary"):
        st.session_state.current_stock_code = item['stock_code']
        st.session_state.search_input_value = history_display_name # 검색창에도 반영
        st.session_state.show_search_results = False # 검색 결과가 떠있었다면 숨김
        logger.info(f"Item selected from history: {history_display_name}, Code: {item['stock_code']}")
        st.rerun()


# 4. 최종 종목 코드 확인 (주로 디버깅 또는 명시적 확인용)
# st.sidebar.caption(f"현재 선택된 종목 코드: {st.session_state.current_stock_code}")


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

final_stock_code_to_analyze = st.session_state.current_stock_code

if analyze_button and final_stock_code_to_analyze:
    # ... (이하 메인 분석 로직은 이전과 동일하게 final_stock_code_to_analyze 사용) ...
    logger.info(f"Analysis started for stock code: {final_stock_code_to_analyze} by user: {user_id}")
    
    with st.spinner("기업 정보 조회 중..."):
        company_info = fetch_company_info(final_stock_code_to_analyze)
        company_name = company_info.get('corp_name', f"종목({final_stock_code_to_analyze})")
        if (company_name == f"종목({final_stock_code_to_analyze})" or company_name is None) and not all_stocks_df.empty:
            match = all_stocks_df[all_stocks_df['Symbol'] == final_stock_code_to_analyze]
            if not match.empty:
                company_name_krx = match['Name'].iloc[0]
                if company_name_krx:
                    company_name = company_name_krx
                    logger.info(f"Company name updated from KRX list: {company_name}")
                    company_info['corp_name'] = company_name

    st.header(f"분석 결과: {company_name} ({final_stock_code_to_analyze})")
    save_user_search(user_id, final_stock_code_to_analyze, company_name)

    tab1, tab2 = st.tabs(["💰 기업 분석 (재무)", "📈 기술적 분석 (차트)"])

    with tab1:
        st.subheader("재무 분석 및 전략 해석")
        try:
            with st.spinner("DART 재무 데이터 수집 중..."):
                current_year = str(datetime.now().year - 1)
                financial_data_df = fetch_dart_financial_data(final_stock_code_to_analyze, year=current_year)

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
                st.warning(f"{company_name} ({final_stock_code_to_analyze})에 대한 DART 재무 데이터를 가져올 수 없습니다. (지원되지 않는 종목이거나 데이터가 없을 수 있습니다)")
        
        except Exception as e:
            st.error(f"기업 분석 중 오류 발생: {e}")
            logger.error(f"Error in financial analysis pipeline for {final_stock_code_to_analyze}: {e}", exc_info=True)

    with tab2:
        st.subheader("차트 분석 및 단기 시나리오")
        try:
            with st.spinner(f"주가 데이터 수집 중... (기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})"):
                price_data_df = fetch_stock_price_data(final_stock_code_to_analyze, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

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
                st.warning(f"{company_name} ({final_stock_code_to_analyze})에 대한 주가 데이터를 가져올 수 없습니다.")
        
        except Exception as e:
            st.error(f"기술적 분석 중 오류 발생: {e}")
            logger.error(f"Error in technical analysis pipeline for {final_stock_code_to_analyze}: {e}", exc_info=True)


elif analyze_button and not final_stock_code_to_analyze:
    st.error("종목 코드를 입력하거나 선택해주세요.")
else:
    if not analyze_button: # 최초 실행 시 또는 분석 버튼 누르기 전
        st.info("좌측 사이드바에서 분석할 종목을 검색하여 선택하거나, 종목 코드를 직접 입력한 후 '분석 실행' 버튼을 클릭하세요.")
    # else: 이미 버튼 눌렀는데 코드 없는 경우는 위에서 처리됨


st.sidebar.markdown("---")
st.sidebar.markdown("제작: @hyunjin_is_good")
st.sidebar.markdown("Ver 0.5 (MVP)")
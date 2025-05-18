
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
    # current_stock_code에 해당하는 기업명을 찾아 초기값 설정
    temp_df = st.session_state.get('krx_stocks_df', pd.DataFrame())
    if not temp_df.empty:
        match = temp_df[temp_df['Symbol'] == st.session_state.current_stock_code]
        if not match.empty:
            st.session_state.search_input_value = f"{match['Name'].iloc[0]} ({st.session_state.current_stock_code})"
        else:
            st.session_state.search_input_value = st.session_state.current_stock_code
    else:
        st.session_state.search_input_value = st.session_state.current_stock_code
    logger.info(f"Initialized search_input_value: {st.session_state.search_input_value}")


if 'show_search_results' not in st.session_state:
    st.session_state.show_search_results = False

if 'filtered_search_results' not in st.session_state:
    st.session_state.filtered_search_results = pd.DataFrame()

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
    current_input = st.session_state.stock_search_input_key # text_input의 현재 값
    st.session_state.search_input_value = current_input # 세션 상태에 반영

    if current_input and len(current_input) >= 1: # 한 글자부터 검색 (사용자 편의)
        if not all_stocks_df.empty:
            # 기업명 또는 종목코드로 검색
            # 사용자가 "(005930)" 같은 형태로 입력한 경우 괄호와 코드 제외하고 이름만으로도 검색되도록
            name_to_search = current_input.split(' (')[0]

            name_mask = all_stocks_df['Name'].astype(str).str.contains(name_to_search, case=False, na=False)
            symbol_mask = all_stocks_df['Symbol'].astype(str).str.startswith(current_input) # 코드는 시작부분 일치
            
            filtered_df = all_stocks_df[name_mask | symbol_mask].copy()
            
            if not filtered_df.empty:
                filtered_df['display_name'] = filtered_df['Name'] + " (" + filtered_df['Symbol'] + ")"
            
            st.session_state.filtered_search_results = filtered_df
            st.session_state.show_search_results = True # 검색 결과가 있으면 항상 표시
            logger.info(f"Search for '{current_input}', found {len(filtered_df)} results.")
        else:
            st.session_state.show_search_results = False
            st.session_state.filtered_search_results = pd.DataFrame()
            logger.warning("KRX stock list is empty, cannot perform search.")
    else: 
        st.session_state.show_search_results = False
        st.session_state.filtered_search_results = pd.DataFrame()

# 1. 통합 검색/입력 창
search_input_widget = st.sidebar.text_input( # 위젯 자체를 변수에 할당하지 않음
    "기업명 또는 종목코드 검색/입력",
    value=st.session_state.search_input_value,
    on_change=search_input_changed,
    key="stock_search_input_key", # 이 키를 통해 콜백에서 값을 가져옴
    placeholder="예: 삼성 또는 005930",
    help="기업명(1글자 이상) 또는 종목코드를 입력하세요."
)

# 2. 검색 결과 드롭다운
if st.session_state.show_search_results and not st.session_state.filtered_search_results.empty:
    st.sidebar.markdown("---") 
    st.sidebar.markdown("**검색 결과:**")
    
    results_df = st.session_state.filtered_search_results
    MAX_DISPLAY_RESULTS = 7
    
    def select_searched_item(selected_symbol, selected_display_name):
        st.session_state.current_stock_code = selected_symbol
        st.session_state.search_input_value = selected_display_name 
        st.session_state.show_search_results = False
        logger.info(f"Item selected from search: {selected_display_name}, Code: {selected_symbol}")
        # st.rerun() # 버튼 클릭 후에는 자동으로 rerun됨

    for i, row_tuple in enumerate(results_df.head(MAX_DISPLAY_RESULTS).itertuples()):
        # itertuples() 사용 시 row_tuple.display_name 등으로 접근
        if st.sidebar.button(f"{row_tuple.display_name}", key=f"search_result_{row_tuple.Symbol}", use_container_width=True):
            select_searched_item(row_tuple.Symbol, row_tuple.display_name)
            st.rerun() # 명시적 rerun으로 즉각 반영

    if len(results_df) > MAX_DISPLAY_RESULTS:
        st.sidebar.caption(f"... 외 {len(results_df) - MAX_DISPLAY_RESULTS}개 더 있음")
    st.sidebar.markdown("---")

# 3. 최근 조회 목록
st.sidebar.markdown("**최근 조회:**")
search_history = get_user_history(user_id, limit=3) # 중복 제거된 기록 가져옴
if not search_history:
    st.sidebar.caption("최근 조회 기록이 없습니다.")

for idx, item in enumerate(user_history):
    history_display_name = item["corp_name"]
    key = f"history_{item['stock_code']}_{idx}"
    if st.sidebar.button(history_display_name, key=key, use_container_width=True, type="secondary"):
        ...

        st.session_state.current_stock_code = item['stock_code']
        st.session_state.search_input_value = history_display_name
        st.session_state.show_search_results = False
        logger.info(f"Item selected from history: {history_display_name}, Code: {item['stock_code']}")
        st.rerun()

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
    logger.info(f"Analysis started for stock code: {final_stock_code_to_analyze} by user: {user_id}")
    
    with st.spinner("기업 정보 조회 중..."):
        company_info = fetch_company_info(final_stock_code_to_analyze) # DART 우선, 실패 시 FDR
        company_name = company_info.get('corp_name', f"종목({final_stock_code_to_analyze})")
        # fetch_company_info에서 이미 FDR 조회를 시도하므로, 여기서는 추가 보강 불필요할 수 있음.
        # 만약 fetch_company_info가 항상 DART만 본다면 여기서 KRX 조회 로직 유지. (현재는 DART 실패 시 FDR 조회)

    st.header(f"분석 결과: {company_name} ({final_stock_code_to_analyze})")
    # 검색 기록 저장 시점: 분석 실행 시 (선택 확정 후)
    if company_name != f"종목({final_stock_code_to_analyze})": # 유효한 회사명을 가져왔을 때만 저장
        save_user_search(user_id, final_stock_code_to_analyze, company_name)
    else: # 회사명을 못가져온 경우, stock_code만으로 저장하거나 저장하지 않을 수 있음
        save_user_search(user_id, final_stock_code_to_analyze, f"기업({final_stock_code_to_analyze})")


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

                    cols[0].metric("ROE (%)", f"{roe_val:.2f}" if isinstance(roe_val, (int,float)) and pd.notna(roe_val) else "N/A")
                    cols[1].metric("부채비율 (%)", f"{debt_ratio_val:.2f}" if isinstance(debt_ratio_val, (int,float)) and pd.notna(debt_ratio_val) else "N/A")
                    cols[2].metric("매출액", f"{sales_val:,.0f}" if isinstance(sales_val, (int, float)) and pd.notna(sales_val) else "N/A")


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
    if not analyze_button : 
        st.info("좌측 사이드바에서 분석할 종목을 검색하여 선택하거나, 종목 코드를 직접 입력한 후 '분석 실행' 버튼을 클릭하세요.")

st.sidebar.markdown("---")
st.sidebar.markdown("제작: 스켈터랩스")
st.sidebar.markdown("Ver 0.6 (MVP)")
import streamlit as st
from datetime import datetime, timedelta

# 모듈 임포트 (프로젝트 구조에 맞게)
from auth import firebase_auth
from data_fetcher import fetch_dart_financial_data, fetch_stock_price_data, fetch_company_info
from financial_analysis import calculate_financial_ratios
from technical_analysis import calculate_technical_indicators
from interpret import interpret_financials, interpret_technicals
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
    # 실제 로그인 UI (예: st.button("Google로 로그인")) 추가 가능

st.sidebar.header("종목 선택")
# 최근 조회 종목을 선택지로 제공
search_history = get_user_history(user_id, limit=5)
history_options = [f"{h['company_name']} ({h['stock_code']})" for h in search_history if h['company_name']]
# 사용자가 직접 입력도 가능하게끔
default_stock_code = search_history[0]['stock_code'] if search_history else "005930" # 기본값: 삼성전자 또는 최근 종목
selected_history = st.sidebar.selectbox("최근 조회 종목", options=["직접 입력"] + history_options)

if selected_history != "직접 입력":
    stock_code_input = selected_history.split('(')[-1][:-1] # "삼성전자 (005930)" -> "005930"
else:
    stock_code_input = ""

stock_code = st.sidebar.text_input("종목 코드 입력", value=stock_code_input or default_stock_code, placeholder="예: 005930").strip()

# 분석 기간 설정 (기술적 분석용)
st.sidebar.header("분석 기간 (기술적 분석)")
# 사용자의 마지막 설정 불러오기 또는 기본값
default_days_ago = get_user_setting(user_id, "analysis_period_days", 90) 

# 옵션 제공
period_options_map = {"3개월": 90, "6개월": 180, "1년": 365, "2년": 730}
selected_period_label = st.sidebar.radio(
    "기간 선택",
    options=list(period_options_map.keys()),
    index = list(period_options_map.values()).index(default_days_ago) if default_days_ago in period_options_map.values() else 0 # 저장된 값으로 기본 선택
)
days_to_subtract = period_options_map[selected_period_label]

# 선택된 기간 저장
if days_to_subtract != default_days_ago:
    save_user_setting(user_id, "analysis_period_days", days_to_subtract)


end_date = datetime.now()
start_date = end_date - timedelta(days=days_to_subtract)

analyze_button = st.sidebar.button("📈 분석 실행", use_container_width=True)

# --- 메인 화면 ---
st.title("📊 AI 기반 국내 주식 분석 도구 (MVP)")

if analyze_button and stock_code:
    logger.info(f"Analysis started for stock code: {stock_code} by user: {user_id}")
    
    # 0. 기업 정보 가져오기
    with st.spinner("기업 정보 조회 중..."):
        company_info = fetch_company_info(stock_code)
        company_name = company_info.get('corp_name', f"종목({stock_code})")
    st.header(f"분석 결과: {company_name} ({stock_code})")

    # 사용자 검색 기록 저장
    save_user_search(user_id, stock_code, company_name)

    # 탭 구성
    tab1, tab2 = st.tabs(["💰 기업 분석 (재무)", "📈 기술적 분석 (차트)"])

    # 1. 기업 분석 파이프라인
    with tab1:
        st.subheader("재무 분석 및 전략 해석")
        try:
            with st.spinner("DART 재무 데이터 수집 중... (MVP: Mock 데이터 사용)"):
                # OpenDART는 사업연도(YYYY)와 분기코드(11011:1분기, 11012:반기, 11013:3분기, 11014:사업보고서) 필요
                # MVP에서는 최근 연도 사업보고서 기준 가정
                current_year = str(datetime.now().year -1) # 보통 작년 사업보고서가 최신
                financial_data_df = fetch_dart_financial_data(stock_code, year=current_year)

            if not financial_data_df.empty:
                with st.spinner("재무 지표 계산 중..."):
                    financial_ratios = calculate_financial_ratios(financial_data_df)
                
                if financial_ratios and "error" not in financial_ratios :
                    st.write("#### 주요 재무 지표")
                    #st.json(financial_ratios) # 데이터 확인용
                    
                    # 주요 지표 표시
                    cols = st.columns(3)
                    cols[0].metric("ROE (%)", f"{financial_ratios.get('ROE (%)', 'N/A'):.2f}" if isinstance(financial_ratios.get('ROE (%)'), float) else "N/A")
                    cols[1].metric("부채비율 (%)", f"{financial_ratios.get('부채비율 (%)', 'N/A'):.2f}" if isinstance(financial_ratios.get('부채비율 (%)'), float) else "N/A")
                    sales_val = financial_ratios.get('매출액', 'N/A')
                    cols[2].metric("매출액", f"{sales_val:,.0f}" if isinstance(sales_val, (int, float)) else "N/A")


                    with st.spinner("재무 요약 차트 생성 중..."):
                        fig_financial_summary = plot_financial_summary(financial_ratios, company_name)
                        st.plotly_chart(fig_financial_summary, use_container_width=True)

                    with st.spinner("전략 해석 메시지 생성 중..."):
                        financial_interpretation = interpret_financials(financial_ratios, company_name)
                        st.info(financial_interpretation)
                else:
                    st.error(f"{company_name}의 재무 지표를 계산할 수 없습니다. (데이터 부족 또는 오류: {financial_ratios.get('error', '')})")
                    # st.dataframe(financial_data_df) # 원본 데이터 확인용
            else:
                st.warning(f"{company_name} ({stock_code})에 대한 DART 재무 데이터를 가져올 수 없습니다. (지원되지 않는 종목이거나 데이터가 없을 수 있습니다)")
        
        except Exception as e:
            st.error(f"기업 분석 중 오류 발생: {e}")
            logger.error(f"Error in financial analysis pipeline for {stock_code}: {e}", exc_info=True)

    # 2. 기술적 분석 파이프라인
    with tab2:
        st.subheader("차트 분석 및 단기 시나리오")
        try:
            with st.spinner(f"주가 데이터 수집 중... (기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}, MVP: Mock 데이터 사용)"):
                price_data_df = fetch_stock_price_data(stock_code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

            if not price_data_df.empty:
                with st.spinner("기술적 지표 계산 중..."):
                    price_df_with_indicators = calculate_technical_indicators(price_data_df.copy()) # 원본 보존 위해 복사
                
                # st.dataframe(price_df_with_indicators.tail()) # 데이터 확인용

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
    st.info("좌측 사이드바에서 분석할 종목 코드를 입력하고 '분석 실행' 버튼을 클릭하세요.")

st.sidebar.markdown("---")
st.sidebar.markdown("제작: [Your Name/Team]")
st.sidebar.markdown("Ver 0.1 (MVP)")
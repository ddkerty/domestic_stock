import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from utils import get_logger

logger = get_logger(__name__)

def plot_comprehensive_analysis(price_df_with_indicators: pd.DataFrame, 
                               company_name: str = "", 
                               fib_levels: dict = None,
                               show_indicators: list = None):
    """
    종합 기술적 분석 차트 생성 (캔들스틱 + MACD + RSI + 피보나치)
    """
    logger.info(f"Plotting comprehensive analysis for {company_name}")
    
    if price_df_with_indicators.empty:
        return create_empty_chart(f"{company_name} 종합 분석 (데이터 없음)")
    
    # 기본 표시할 지표 설정
    if show_indicators is None:
        show_indicators = ['MA', 'MACD', 'RSI', 'Fibonacci']
    
    # 서브플롯 구성 결정
    subplot_count = 1  # 기본 캔들스틱
    subplot_heights = [0.6]  # 캔들스틱이 가장 큰 비중
    subplot_titles = [f"{company_name} 주가"]
    
    if 'MACD' in show_indicators:
        subplot_count += 1
        subplot_heights.append(0.2)
        subplot_titles.append("MACD")
    
    if 'RSI' in show_indicators:
        subplot_count += 1
        subplot_heights.append(0.2)
        subplot_titles.append("RSI")
    
    # 높이 정규화
    total_height = sum(subplot_heights)
    subplot_heights = [h/total_height for h in subplot_heights]
    
    # 서브플롯 생성
    fig = make_subplots(
        rows=subplot_count, 
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=subplot_titles,
        row_heights=subplot_heights,
        specs=[[{"secondary_y": False}] for _ in range(subplot_count)]
    )
    
    current_row = 1
    
    # 1. 캔들스틱 차트 (메인)
    fig.add_trace(
        go.Candlestick(
            x=price_df_with_indicators['Date'],
            open=price_df_with_indicators['Open'],
            high=price_df_with_indicators['High'],
            low=price_df_with_indicators['Low'],
            close=price_df_with_i

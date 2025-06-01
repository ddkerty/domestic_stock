import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from utils import get_logger

logger = get_logger(__name__)

def create_empty_chart(title):
    """데이터가 없을 때 표시할 빈 차트를 생성합니다."""
    fig = go.Figure()
    fig.update_layout(
        title_text=title,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[{
            "text": "차트 데이터가 없습니다.",
            "xref": "paper",
            "yref": "paper",
            "showarrow": False,
            "font": {"size": 20}
        }]
    )
    return fig

def plot_financial_summary(ratios: dict, company_name: str) -> go.Figure:
    """재무 비율 데이터를 사용하여 바 차트를 생성합니다."""
    if not ratios or "error" in ratios:
        return create_empty_chart(f"{company_name} 재무 데이터 요약")
    
    # 유효한 숫자 데이터만 필터링
    plot_data = {k: v for k, v in ratios.items() if isinstance(v, (int, float))}
    
    if not plot_data:
        return create_empty_chart(f"{company_name} 재무 데이터 요약 (표시할 데이터 없음)")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(plot_data.keys()),
        y=list(plot_data.values()),
        text=[f'{v:,.2f}' for v in plot_data.values()],
        textposition='auto',
        marker_color='indianred'
    ))
    fig.update_layout(
        title_text=f"{company_name} 재무 핵심 지표",
        xaxis_title="재무 지표",
        yaxis_title="값",
        uniformtext_minsize=8, 
        uniformtext_mode='hide'
    )
    return fig

def plot_candlestick_with_indicators(price_df: pd.DataFrame, company_name: str) -> go.Figure:
    """기술적 지표가 포함된 캔들스틱 차트를 생성합니다."""
    if price_df.empty:
        return create_empty_chart(f"{company_name} 주가 차트")
        
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        subplot_titles=(f'{company_name} 주가', 'RSI'), 
        row_heights=[0.7, 0.3]
    )

    # 1. 캔들스틱 및 이동평균선
    fig.add_trace(go.Candlestick(
        x=price_df['Date'],
        open=price_df['Open'],
        high=price_df['High'],
        low=price_df['Low'],
        close=price_df['Close'],
        name='캔들스틱'
    ), row=1, col=1)

    if 'SMA_5' in price_df.columns:
        fig.add_trace(go.Scatter(x=price_df['Date'], y=price_df['SMA_5'], name='5일 이평선', line=dict(color='blue', width=1)), row=1, col=1)
    if 'SMA_20' in price_df.columns:
        fig.add_trace(go.Scatter(x=price_df['Date'], y=price_df['SMA_20'], name='20일 이평선', line=dict(color='orange', width=1)), row=1, col=1)
    
    # 2. RSI
    if 'RSI' in price_df.columns:
        fig.add_trace(go.Scatter(x=price_df['Date'], y=price_df['RSI'], name='RSI', line=dict(color='purple', width=1)), row=2, col=1)
        fig.add_hline(y=70, col=1, row=2, line_width=1, line_dash="dash", line_color="red")
        fig.add_hline(y=30, col=1, row=2, line_width=1, line_dash="dash", line_color="blue")

    fig.update_layout(
        title_text=f"{company_name} 기술적 분석 차트",
        xaxis_rangeslider_visible=False,
        legend_title="지표"
    )
    fig.update_yaxes(title_text="주가 (KRW)", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1)
    
    return fig

# 이 함수는 현재 app.py에서 직접 사용되진 않지만, 향후 확장을 위해 남겨둡니다.
def plot_comprehensive_analysis(price_df_with_indicators: pd.DataFrame, company_name: str = ""):
    """종합 기술적 분석 차트 생성 (캔들스틱 + MACD + RSI 등)"""
    # 이 함수는 위 plot_candlestick_with_indicators 함수로 대체하여 사용하거나,
    # 필요에 따라 더 많은 지표를 추가하여 확장할 수 있습니다.
    # 현재는 plot_candlestick_with_indicators가 메인 차트 함수로 사용됩니다.
    logger.info(f"Comprehensive analysis plot for {company_name}")
    
    # --- START: 수정된 라인 ---
    # 이 함수는 이제 plot_candlestick_with_indicators에 통합되었으므로, 해당 함수를 호출합니다.
    return plot_candlestick_with_indicators(price_df_with_indicators, company_name)
    # --- END: 수정된 라인 ---
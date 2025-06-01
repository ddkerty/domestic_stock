import plotly.graph_objects as go
import pandas as pd
from utils import get_logger
from plotly.subplots import make_subplots # <-- 수정된 부분: make_subplots 임포트 추가

logger = get_logger(__name__)

def create_empty_chart(title):
    """데이터가 없을 때 표시할 빈 차트를 생성합니다."""
    fig = go.Figure()
    fig.update_layout(
        title_text=title,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[{
            "text": "데이터가 없습니다.",
            "xref": "paper",
            "yref": "paper",
            "showarrow": False,
            "font": {"size": 20}
        }]
    )
    return fig

def plot_financial_kpis(ratios: dict):
    """
    주요 재무 지표(ROE, 부채비율, 매출액)에 대한 개별 KPI 차트 3개를 생성합니다.
    """
    theme = {'template': 'plotly_dark'}
    
    roe_val = ratios.get("ROE (%)", 0)
    roe_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=float(f"{roe_val:.2f}"),
        title={'text': "<b>ROE (%)</b><br><span style='font-size:0.8em;color:gray'>자기자본이익률</span>", 'font': {'size': 16}},
        gauge={
            'axis': {'range': [-20, 50], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "#636EFA"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [-20, 0], 'color': 'rgba(239, 85, 59, 0.2)'},
                {'range': [0, 15], 'color': 'rgba(99, 110, 250, 0.2)'}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 15}
        }
    ))
    roe_fig.update_layout(**theme, height=250)

    debt_val = ratios.get("부채비율 (%)", 0)
    debt_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=float(f"{debt_val:.2f}"),
        title={'text': "<b>부채비율 (%)</b><br><span style='font-size:0.8em;color:gray'>안정성 지표</span>", 'font': {'size': 16}},
        gauge={
            'axis': {'range': [0, 400], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "#EF553B"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 100], 'color': 'rgba(0, 204, 150, 0.2)'},
                {'range': [100, 200], 'color': 'rgba(255, 255, 0, 0.25)'}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 200}
        }
    ))
    debt_fig.update_layout(**theme, height=250)

    sales_val = ratios.get("매출액", 0)
    sales_in_b_won = sales_val / 100000000 if sales_val else 0
    sales_fig = go.Figure(go.Indicator(
        mode="number",
        value=sales_in_b_won,
        title={'text': "<b>매출액 (억원)</b><br><span style='font-size:0.8em;color:gray'>성장성 지표</span>", 'font': {'size': 16}},
        number={'valueformat': ',.0f'}
    ))
    sales_fig.update_layout(**theme, height=250)

    return roe_fig, debt_fig, sales_fig

def plot_candlestick_with_indicators(price_df: pd.DataFrame, company_name: str) -> go.Figure:
    """기술적 지표가 포함된 캔들스틱 차트를 생성합니다."""
    if price_df.empty:
        return create_empty_chart(f"{company_name} 주가 차트")
        
    fig = make_subplots( # <-- make_subplots 함수 사용
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        subplot_titles=(f'{company_name} 주가', 'RSI'), 
        row_heights=[0.7, 0.3]
    )

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
    
    if 'RSI' in price_df.columns:
        fig.add_trace(go.Scatter(x=price_df['Date'], y=price_df['RSI'], name='RSI', line=dict(color='purple', width=1)), row=2, col=1)
        fig.add_hline(y=70, col=1, row=2, line_width=1, line_dash="dash", line_color="red")
        fig.add_hline(y=30, col=1, row=2, line_width=1, line_dash="dash", line_color="blue")

    fig.update_layout(
        title_text=f"{company_name} 기술적 분석 차트",
        xaxis_rangeslider_visible=False,
        legend_title="지표",
        template='plotly_dark'
    )
    fig.update_yaxes(title_text="주가 (KRW)", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1)
    
    return fig
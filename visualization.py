import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from .utils import get_logger

logger = get_logger(__name__)

def plot_financial_summary(ratios: dict, company_name: str = ""):
    """
    재무 요약 정보를 차트로 시각화합니다 (예: 주요 비율 바 차트).
    """
    logger.info(f"Plotting financial summary for {company_name}")
    if not ratios or not any(isinstance(v, (int, float)) for v in ratios.values()): # 숫자형 데이터가 있는지 확인
        logger.warning("No valid financial ratios to plot.")
        fig = go.Figure()
        fig.update_layout(title_text=f"{company_name} 재무 요약 (데이터 없음)",
                          xaxis_showgrid=False, yaxis_showgrid=False,
                          annotations=[dict(text="표시할 재무 데이터가 없습니다.", xref="paper", yref="paper",
                                            showarrow=False, font=dict(size=16))])
        return fig

    # 유효한 숫자 데이터만 필터링
    plot_data = {k: v for k, v in ratios.items() if isinstance(v, (int, float))}
    if not plot_data:
        logger.warning("No numeric financial ratios to plot after filtering.")
        # (위와 동일한 데이터 없음 메시지 처리)
        fig = go.Figure()
        fig.update_layout(title_text=f"{company_name} 재무 요약 (숫자 데이터 없음)",
                          xaxis_showgrid=False, yaxis_showgrid=False,
                          annotations=[dict(text="표시할 숫자형 재무 데이터가 없습니다.", xref="paper", yref="paper",
                                            showarrow=False, font=dict(size=16))])
        return fig
        
    try:
        # 간단한 바 차트 예시
        df = pd.DataFrame(list(plot_data.items()), columns=['지표', '값'])
        fig = px.bar(df, x='지표', y='값', title=f"{company_name} 주요 재무 지표", text='값')
        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
        return fig
    except Exception as e:
        logger.error(f"Error plotting financial summary: {e}")
        fig = go.Figure()
        fig.update_layout(title_text=f"{company_name} 재무 요약 (차트 생성 오류)",
                          annotations=[dict(text=f"차트 생성 중 오류: {e}", xref="paper", yref="paper",
                                            showarrow=False, font=dict(size=16))])
        return fig


def plot_candlestick_with_indicators(price_df_with_indicators: pd.DataFrame, company_name: str = ""):
    """
    캔들 차트와 기술적 지표(이동평균선 등)를 오버레이하여 출력합니다.
    """
    logger.info(f"Plotting candlestick chart for {company_name}")
    if price_df_with_indicators.empty or not all(col in price_df_with_indicators.columns for col in ['Date', 'Open', 'High', 'Low', 'Close']):
        logger.warning("Price data is insufficient for candlestick chart.")
        fig = go.Figure()
        fig.update_layout(title_text=f"{company_name} 주가 차트 (데이터 없음)",
                          xaxis_showgrid=False, yaxis_showgrid=False,
                          annotations=[dict(text="표시할 주가 데이터가 없습니다.", xref="paper", yref="paper",
                                            showarrow=False, font=dict(size=16))])
        return fig

    fig = go.Figure()

    # 캔들스틱 차트
    fig.add_trace(go.Candlestick(x=price_df_with_indicators['Date'],
                                 open=price_df_with_indicators['Open'],
                                 high=price_df_with_indicators['High'],
                                 low=price_df_with_indicators['Low'],
                                 close=price_df_with_indicators['Close'],
                                 name='캔들스틱'))

    # 이동평균선 추가 (존재하는 경우)
    if 'SMA_5' in price_df_with_indicators.columns and price_df_with_indicators['SMA_5'].notna().any():
        fig.add_trace(go.Scatter(x=price_df_with_indicators['Date'], y=price_df_with_indicators['SMA_5'],
                                 mode='lines', name='SMA 5일', line=dict(color='orange', width=1)))
    if 'SMA_20' in price_df_with_indicators.columns and price_df_with_indicators['SMA_20'].notna().any():
        fig.add_trace(go.Scatter(x=price_df_with_indicators['Date'], y=price_df_with_indicators['SMA_20'],
                                 mode='lines', name='SMA 20일', line=dict(color='purple', width=1)))
    
    # VWAP 추가 (존재하는 경우)
    if 'VWAP_daily_approx' in price_df_with_indicators.columns and price_df_with_indicators['VWAP_daily_approx'].notna().any():
        fig.add_trace(go.Scatter(x=price_df_with_indicators['Date'], y=price_df_with_indicators['VWAP_daily_approx'],
                                 mode='lines', name='VWAP (일별 근사)', line=dict(color='blue', dash='dash', width=1)))


    # 차트 레이아웃 설정
    fig.update_layout(
        title=f"{company_name} 주가 및 기술적 지표",
        xaxis_title="날짜",
        yaxis_title="가격",
        xaxis_rangeslider_visible=False, # 하단 레인지 슬라이더 숨김 (취향따라)
        legend_title_text="지표"
    )
    
    return fig
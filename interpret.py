
import pandas as pd # 이 줄을 추가해주세요
from utils import get_logger

logger = get_logger(__name__)

def interpret_financials(ratios: dict, company_name: str = ""):
    """
    계산된 재무 지표를 바탕으로 해석 메시지를 생성합니다.
    """
    logger.info(f"Interpreting financial ratios for {company_name}: {ratios}")
    if not ratios or "ROE (%)" not in ratios or "부채비율 (%)" not in ratios: # 주요 지표 확인
        return f"{company_name}의 재무 지표를 해석할 수 없습니다. 데이터가 부족하거나 오류가 발생했습니다."

    interpretation = f"📜 **{company_name} 재무 분석 해석**\n"
    
    roe = ratios.get("ROE (%)")
    debt_ratio = ratios.get("부채비율 (%)")
    sales = ratios.get("매출액", "N/A")

    if roe is not None:
        if roe > 15:
            interpretation += f"- ROE(자기자본이익률)는 **{roe:.2f}%**로, 비교적 높은 수익성을 보입니다. 자기자본 대비 이익 창출 능력이 우수하다고 평가할 수 있습니다.\n"
        elif roe > 5:
            interpretation += f"- ROE(자기자본이익률)는 **{roe:.2f}%**로, 보통 수준의 수익성을 보입니다.\n"
        else:
            interpretation += f"- ROE(자기자본이익률)는 **{roe:.2f}%**로, 다소 낮은 수익성을 보입니다. 투자 대비 효율성 개선이 필요할 수 있습니다.\n"
    else:
        interpretation += "- ROE 정보를 가져오지 못했습니다.\n"

    if debt_ratio is not None:
        if debt_ratio < 100:
            interpretation += f"- 부채비율은 **{debt_ratio:.2f}%**로, 매우 안정적인 재무 구조를 가지고 있습니다. 타인자본 의존도가 낮습니다.\n"
        elif debt_ratio < 200:
            interpretation += f"- 부채비율은 **{debt_ratio:.2f}%**로, 적정 수준 또는 다소 높은 편입니다. 재무 안정성을 지속적으로 확인할 필요가 있습니다.\n"
        else:
            interpretation += f"- 부채비율은 **{debt_ratio:.2f}%**로, 높은 수준입니다. 재무적 위험 관리에 유의해야 합니다.\n"
    else:
        interpretation += "- 부채비율 정보를 가져오지 못했습니다.\n"
        
    # 매출액이 숫자인 경우에만 포맷팅 시도
    if isinstance(sales, (int, float)):
        interpretation += f"- 최근 보고된 매출액은 약 **{sales:,.0f}** (단위: DART 제공 단위 확인 필요, 보통 천원 또는 백만원) 입니다.\n"
    else:
        interpretation += f"- 최근 보고된 매출액: **{sales}**\n" # 숫자가 아니면 그대로 표시
    
    interpretation += "\n*주의: 위 해석은 제공된 수치를 기반으로 한 일반적인 의견이며, 투자 결정은 다양한 정보를 종합적으로 고려하여 신중하게 이루어져야 합니다.*"
    
    return interpretation

def interpret_technicals(price_df_with_indicators: pd.DataFrame, company_name: str = ""):
    """
    계산된 기술적 지표를 바탕으로 단기 시나리오 해석을 출력합니다.
    """
    logger.info(f"Interpreting technical indicators for {company_name}")
    if price_df_with_indicators.empty:
        return f"{company_name}의 기술적 지표를 해석할 수 없습니다. 데이터가 부족합니다."

    interpretation = f"📈 **{company_name} 기술적 분석 해석 (최근 데이터 기준)**\n"
    
    # 마지막 데이터 포인트 사용
    last_data = price_df_with_indicators.iloc[-1] if not price_df_with_indicators.empty else None

    if last_data is not None:
        current_close = last_data.get('Close', 'N/A')
        interpretation += f"- 현재 종가: **{current_close:,.0f if isinstance(current_close, (int, float)) else current_close}** (해당 날짜: {last_data.get('Date', 'N/A').strftime('%Y-%m-%d') if pd.notna(last_data.get('Date')) and hasattr(last_data.get('Date'), 'strftime') else 'N/A'})\n" # hasattr 추가

        if 'SMA_5' in last_data and 'SMA_20' in last_data and pd.notna(last_data['SMA_5']) and pd.notna(last_data['SMA_20']):
            sma5 = last_data['SMA_5']
            sma20 = last_data['SMA_20']
            interpretation += f"- 단기 이동평균(5일): {sma5:,.0f}, 중기 이동평균(20일): {sma20:,.0f}\n"
            if sma5 > sma20 and (isinstance(current_close, (int, float)) and current_close > sma5): # current_close 타입 확인
                interpretation += "  - 단기 상승 추세가 나타나고 있으며, 현재 주가가 단기 이평선 위에 있어 긍정적 신호로 볼 수 있습니다. (골든 크로스 근접 또는 발생 가능성)\n"
            elif sma5 < sma20 and (isinstance(current_close, (int, float)) and current_close < sma5): # current_close 타입 확인
                interpretation += "  - 단기 하락 추세가 나타나고 있으며, 현재 주가가 단기 이평선 아래에 있어 주의가 필요합니다. (데드 크로스 근접 또는 발생 가능성)\n"
            else:
                interpretation += "  - 이동평균선들이 혼조세를 보이거나 주가가 이평선 사이에 위치하여 방향성 탐색 구간일 수 있습니다.\n"
        else:
            interpretation += "- 이동평균선 정보를 충분히 계산하지 못했습니다.\n"
            
        # RSI, MACD 등 추가 지표 해석 로직 (TA-Lib 사용 시)
        # if 'RSI_14' in last_data and pd.notna(last_data['RSI_14']):
        #     rsi = last_data['RSI_14']
        #     interpretation += f"- RSI(14): {rsi:.2f}\n"
        #     if rsi > 70:
        #         interpretation += "  - RSI가 70 이상으로 과매수 구간에 진입했을 수 있습니다. 단기 조정 가능성에 유의해야 합니다.\n"
        #     elif rsi < 30:
        #         interpretation += "  - RSI가 30 이하로 과매도 구간에 진입했을 수 있습니다. 단기 반등 가능성을 주시할 수 있습니다.\n"
        #     else:
        #         interpretation += "  - RSI가 중립 구간에 있어 현재 추세가 이어지거나 횡보할 수 있습니다.\n"
    
    else:
        interpretation += "- 최근 가격 데이터가 없어 기술적 해석이 어렵습니다.\n"

    interpretation += "\n*주의: 위 해석은 단순 지표에 기반한 의견이며, 실제 투자 결정은 다양한 요소와 시장 상황을 종합적으로 고려해야 합니다.*"
    
    return interpretation
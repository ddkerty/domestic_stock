
import pandas as pd
from utils import get_logger

logger = get_logger(__name__)

def interpret_financials(ratios: dict, company_name: str = ""):
    # ... (이전과 동일) ...
    logger.info(f"Interpreting financial ratios for {company_name}: {ratios}")
    if not ratios or not isinstance(ratios, dict) or "error" in ratios:
        error_msg = ratios.get("error", "데이터 부족") if isinstance(ratios, dict) else "데이터 포맷 오류"
        return f"{company_name}의 재무 지표를 해석할 수 없습니다. ({error_msg})"

    interpretation = f"📜 **{company_name} 재무 분석 해석**\n"
    
    roe = ratios.get("ROE (%)")
    debt_ratio = ratios.get("부채비율 (%)")
    sales = ratios.get("매출액") 

    if roe is not None and isinstance(roe, (int, float)):
        if roe > 15:
            interpretation += f"- ROE(자기자본이익률)는 **{roe:.2f}%**로, 비교적 높은 수익성을 보입니다. 자기자본 대비 이익 창출 능력이 우수하다고 평가할 수 있습니다.\n"
        elif roe > 5:
            interpretation += f"- ROE(자기자본이익률)는 **{roe:.2f}%**로, 보통 수준의 수익성을 보입니다.\n"
        else:
            interpretation += f"- ROE(자기자본이익률)는 **{roe:.2f}%**로, 다소 낮은 수익성을 보입니다. 투자 대비 효율성 개선이 필요할 수 있습니다.\n"
    else:
        interpretation += "- ROE 정보를 가져오지 못했거나 유효하지 않습니다.\n"

    if debt_ratio is not None and isinstance(debt_ratio, (int, float)):
        if debt_ratio < 100:
            interpretation += f"- 부채비율은 **{debt_ratio:.2f}%**로, 매우 안정적인 재무 구조를 가지고 있습니다. 타인자본 의존도가 낮습니다.\n"
        elif debt_ratio < 200:
            interpretation += f"- 부채비율은 **{debt_ratio:.2f}%**로, 적정 수준 또는 다소 높은 편입니다. 재무 안정성을 지속적으로 확인할 필요가 있습니다.\n"
        else:
            interpretation += f"- 부채비율은 **{debt_ratio:.2f}%**로, 높은 수준입니다. 재무적 위험 관리에 유의해야 합니다.\n"
    else:
        interpretation += "- 부채비율 정보를 가져오지 못했거나 유효하지 않습니다.\n"
        
    if sales is not None and isinstance(sales, (int, float)):
        interpretation += f"- 최근 보고된 매출액은 약 **{sales:,.0f}** (단위: DART 제공 단위 확인 필요, 보통 천원 또는 백만원) 입니다.\n"
    else:
        interpretation += f"- 최근 보고된 매출액 정보를 가져오지 못했거나 유효하지 않습니다.\n"
    
    interpretation += "\n*주의: 위 해석은 제공된 수치를 기반으로 한 일반적인 의견이며, 투자 결정은 다양한 정보를 종합적으로 고려하여 신중하게 이루어져야 합니다.*"
    
    return interpretation

def interpret_technicals(price_df_with_indicators: pd.DataFrame, company_name: str = ""):
    logger.info(f"Interpreting technical indicators for {company_name}")
    if price_df_with_indicators.empty:
        return f"{company_name}의 기술적 지표를 해석할 수 없습니다. 데이터가 부족합니다."

    interpretation = f"📈 **{company_name} 기술적 분석 해석 (최근 데이터 기준)**\n"
    
    last_data = price_df_with_indicators.iloc[-1] if not price_df_with_indicators.empty else None

    if last_data is not None:
        current_close_val = last_data.get('Close')
        
        # 수정된 부분: current_close_display 값을 외부에서 미리 준비
        if isinstance(current_close_val, (int, float)):
            current_close_display = f"{current_close_val:,.0f}"
        else:
            current_close_display = "N/A"
        
        date_val = last_data.get('Date')
        date_display = date_val.strftime('%Y-%m-%d') if pd.notna(date_val) and hasattr(date_val, 'strftime') else "N/A"
        interpretation += f"- 현재 종가: **{current_close_display}** (해당 날짜: {date_display})\n" # 수정된 current_close_display 사용

        sma5_val = last_data.get('SMA_5')
        sma20_val = last_data.get('SMA_20')

        if pd.notna(sma5_val) and pd.notna(sma20_val) and isinstance(current_close_val, (int,float)): # current_close_val 타입 체크
            sma5_display = f"{sma5_val:,.0f}"
            sma20_display = f"{sma20_val:,.0f}"
            interpretation += f"- 단기 이동평균(5일): {sma5_display}, 중기 이동평균(20일): {sma20_display}\n"
            if sma5_val > sma20_val and current_close_val > sma5_val :
                interpretation += "  - 단기 상승 추세가 나타나고 있으며, 현재 주가가 단기 이평선 위에 있어 긍정적 신호로 볼 수 있습니다. (골든 크로스 근접 또는 발생 가능성)\n"
            elif sma5_val < sma20_val and current_close_val < sma5_val:
                interpretation += "  - 단기 하락 추세가 나타나고 있으며, 현재 주가가 단기 이평선 아래에 있어 주의가 필요합니다. (데드 크로스 근접 또는 발생 가능성)\n"
            else:
                interpretation += "  - 이동평균선들이 혼조세를 보이거나 주가가 이평선 사이에 위치하여 방향성 탐색 구간일 수 있습니다.\n"
        else:
            interpretation += "- 이동평균선 정보를 충분히 계산하지 못했거나 현재 종가 정보가 유효하지 않습니다.\n"
            
    else:
        interpretation += "- 최근 가격 데이터가 없어 기술적 해석이 어렵습니다.\n"

    interpretation += "\n*주의: 위 해석은 단순 지표에 기반한 의견이며, 실제 투자 결정은 다양한 요소와 시장 상황을 종합적으로 고려해야 합니다.*"
    
    return interpretation
import pandas as pd
from utils import get_logger
from typing import List, Dict

logger = get_logger(__name__)

def interpret_financials(ratios: dict, company_name: str = ""):
    # (이전과 동일)
    if not ratios or not isinstance(ratios, dict) or "error" in ratios:
        return f"{company_name}의 재무 지표를 해석할 수 없습니다."
    
    interpretation = f"📜 **{company_name} 재무 분석 해석**\n\n"
    roe = ratios.get("ROE (%)")
    debt_ratio = ratios.get("부채비율 (%)")
    
    if roe is not None and isinstance(roe, (int, float)):
        if roe > 15:
            interpretation += f"- **ROE(자기자본이익률)**는 **{roe:.2f}%**로, 자기자본 대비 높은 이익을 창출하며 **수익성이 우수**합니다.\n"
        elif roe > 5:
            interpretation += f"- **ROE(자기자본이익률)**는 **{roe:.2f}%**로, **준수한 수준의 수익성**을 보입니다.\n"
        else:
            interpretation += f"- **ROE(자기자본이익률)**는 **{roe:.2f}%**로, **다소 낮은 수익성**을 보입니다. 투자 효율성 개선이 필요할 수 있습니다.\n"
    
    if debt_ratio is not None and isinstance(debt_ratio, (int, float)):
        if debt_ratio < 100:
            interpretation += f"- **부채비율**은 **{debt_ratio:.2f}%**로, 타인자본 의존도가 낮아 **재무적으로 매우 안정적**입니다.\n"
        elif debt_ratio < 200:
            interpretation += f"- **부채비율**은 **{debt_ratio:.2f}%**로, **적정 수준**이나 지속적인 관리가 필요합니다.\n"
        else:
            interpretation += f"- **부채비율**은 **{debt_ratio:.2f}%**로, **높은 수준**이므로 재무적 위험 관리에 유의해야 합니다.\n"

    interpretation += "\n*주의: 위 해석은 제공된 수치를 기반으로 한 일반적인 의견이며, 투자 결정은 다양한 정보를 종합적으로 고려하여 신중하게 이루어져야 합니다.*"
    return interpretation

def interpret_fibonacci(close_value: float, levels: Dict[str, float]) -> str:
    """피보나치 레벨과 현재가를 비교하여 지지/저항 신호를 해석합니다."""
    if not levels:
        return ""

    sorted_levels = sorted(levels.items(), key=lambda item: item[1])
    
    for i in range(len(sorted_levels) - 1):
        lower_level_name = sorted_levels[i][0].split('_')[1]
        lower_level_val = sorted_levels[i][1]
        upper_level_name = sorted_levels[i+1][0].split('_')[1]
        upper_level_val = sorted_levels[i+1][1]

        # 현재가가 두 레벨 사이에 위치하는 경우
        if lower_level_val <= close_value <= upper_level_val:
            return f"🔵 **피보나치:** 현재가({close_value:,.0f})가 **{lower_level_name}%**와 **{upper_level_name}%** 구간 사이에 위치. *해당 구간이 주요 지지/저항선으로 작용할 수 있습니다.*"

    if close_value > sorted_levels[-1][1]:
         return f"🚀 **피보나치:** 현재가가 주요 저항선인 **0.0%** 레벨을 상향 돌파. *추가 상승 기대 가능*"
    if close_value < sorted_levels[0][1]:
         return f"⚓️ **피보나치:** 현재가가 주요 지지선인 **100.0%** 레벨을 하향 이탈. *추가 하락 주의 필요*"
    
    return ""


def interpret_technical_signals(row: pd.Series, df_context: pd.DataFrame, fib_levels: Dict[str, float]) -> List[str]:
    """VWAP, 볼린저 밴드, RSI, MACD, 피보나치 기준 자동 해석"""
    signals = []

    # 📊 VWAP 해석
    if 'VWAP' in row and pd.notna(row['VWAP']):
        if row['Close'] > row['VWAP']:
            signals.append("📈 **VWAP:** 현재가가 VWAP 위에 있어 **단기 매수세가 우위**에 있습니다.")
        else:
            signals.append("📉 **VWAP:** 현재가가 VWAP 아래에 있어 **단기 매도세가 우위**에 있습니다.")

    # 📊 Bollinger Band 해석
    if all(c in row for c in ['Upper', 'Lower']) and pd.notna(row['Upper']):
        if row['Close'] > row['Upper']:
            signals.append("🚨 **볼린저밴드:** 상단선 돌파. **단기 과열 또는 강한 상승 추세**를 의미할 수 있습니다.")
        elif row['Close'] < row['Lower']:
            signals.append("💡 **볼린저밴드:** 하단선 이탈. **단기 낙폭 과대** 상태일 수 있습니다.")
        else:
            signals.append("↔️ **볼린저밴드:** 밴드 내에서 움직이며 **방향성을 탐색** 중입니다.")
            
    # 📊 RSI 해석
    if 'RSI' in row and pd.notna(row['RSI']):
        rsi = row['RSI']
        if rsi > 70:
            signals.append(f"🔥 **RSI ({rsi:.1f}):** 과매수 영역. 단기적인 가격 조정 가능성에 유의해야 합니다.")
        elif rsi < 30:
            signals.append(f"🧊 **RSI ({rsi:.1f}):** 과매도 영역. 기술적 반등 가능성을 기대해볼 수 있습니다.")
        else:
            signals.append(f"🟡 **RSI ({rsi:.1f}):** 중립 영역에서 움직이고 있습니다.")
            
    # 📊 MACD 해석
    if all(c in row for c in ['MACD', 'MACD_signal']) and pd.notna(row['MACD']):
        if row['MACD'] > row['MACD_signal']:
            signals.append("🟢 **MACD:** MACD선이 시그널선 위에 위치하여 **상승 모멘텀**이 우세합니다.")
        else:
            signals.append("🔴 **MACD:** MACD선이 시그널선 아래에 위치하여 **하락 모멘텀**이 우세합니다.")

    # 📊 피보나치 되돌림 해석
    if fib_levels and pd.notna(row['Close']):
        fib_msg = interpret_fibonacci(row['Close'], fib_levels)
        if fib_msg:
            signals.append(fib_msg)
            
    return signals
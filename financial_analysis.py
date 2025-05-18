
import pandas as pd
from utils import get_logger

logger = get_logger(__name__)

def calculate_financial_ratios(financial_df: pd.DataFrame) -> dict:
    """
    DART에서 수신한 재무제표 df를 기반으로 주요 재무 지표 계산
    - ROE: 순이익 / 자기자본
    - 부채비율: 부채총계 / 자본총계
    - 매출액: 직접 반환
    """
    try:
        logger.info("Calculating financial ratios...")

        # 주요 지표 추출을 위한 키워드
        equity_keywords = ["자본총계", "총자본", "자본"]
        debt_keywords = ["부채총계", "총부채", "부채"]
        net_income_keywords = ["당기순이익", "순이익"]
        sales_keywords = ["매출", "수익", "영업수익", "매출액", "매출수익"]

        def find_amount_by_keywords(keywords):
            for keyword in keywords:
                row = financial_df[financial_df['account_nm'].str.contains(keyword, case=False, na=False)]
                if not row.empty:
                    # 가장 최근 항목 하나만
                    amount = row.iloc[0].get('thstrm_amount', None)
                    if pd.notna(amount):
                        return amount
            return None

        equity = find_amount_by_keywords(equity_keywords)
        debt = find_amount_by_keywords(debt_keywords)
        net_income = find_amount_by_keywords(net_income_keywords)
        sales = find_amount_by_keywords(sales_keywords)

        # 금액들이 문자열로 들어오면 숫자형으로
        equity = pd.to_numeric(equity, errors="coerce")
        debt = pd.to_numeric(debt, errors="coerce")
        net_income = pd.to_numeric(net_income, errors="coerce")
        sales = pd.to_numeric(sales, errors="coerce")

        logger.info(f"Calculated - Sales: {sales}, Net Income: {net_income}, Total Equity: {equity}, Total Debt: {debt}")

        roe = (net_income / equity) * 100 if equity and net_income is not None and equity != 0 else 0.0
        debt_ratio = (debt / equity) * 100 if equity and debt is not None and equity != 0 else 0.0

        logger.info(f"Calculated ratios - ROE: {roe}, Debt Ratio: {debt_ratio}")

        return {
            "ROE (%)": roe,
            "부채비율 (%)": debt_ratio,
            "매출액": sales
        }

    except Exception as e:
        logger.error(f"Error in calculating financial ratios: {e}", exc_info=True)
        return {"error": str(e)}
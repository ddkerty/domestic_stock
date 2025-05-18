
import pandas as pd
from utils import get_logger

logger = get_logger(__name__)

def calculate_financial_ratios(financial_df: pd.DataFrame):
    """
    DART 재무제표 데이터를 기반으로 주요 재무 지표를 계산합니다.
    (MVP에서는 단순 계산 또는 목업 값 반환)
    """
    logger.info("Calculating financial ratios...")
    if financial_df.empty:
        logger.warning("Financial data is empty. Cannot calculate ratios.")
        return {"error": "Financial data is empty."} # 에러 메시지를 포함한 dict 반환

    # 실제 재무제표 항목명(account_nm 또는 account_id)과 DART API 응답 구조를 확인해야 함
    # 아래는 매우 단순화된 예시이며, 실제 데이터에 맞게 수정 필요
    
    roe = None
    debt_ratio = None
    sales = 0 # 기본값을 0으로 설정
    
    try:
        # 예시: 매출액, 당기순이익, 자본총계, 부채총계 찾기 (실제 항목명에 따라 수정)
        # 이 부분은 DART에서 가져온 financial_df의 실제 구조에 따라 파싱 로직이 복잡해짐
        # sj_nm (재무상태표/손익계산서)와 account_nm (계정명)을 조합하여 값을 찾아야 함
        
        # 매출액 (손익계산서)
        sales_series = financial_df[
            (financial_df['sj_nm'] == '손익계산서') &
            (financial_df['account_nm'].str.contains('매출액', na=False)) # '유동자산' 등 다른 계정명으로 오인하지 않도록 주의
        ]['thstrm_amount']
        if not sales_series.empty and pd.notna(sales_series.iloc[0]):
            sales = float(sales_series.iloc[0])

        # 당기순이익 (손익계산서)
        net_income_series = financial_df[
            (financial_df['sj_nm'] == '손익계산서') &
            (financial_df['account_nm'].str.contains('당기순이익|포괄손익', na=False)) # 실제 계정명 확인 필요
        ]['thstrm_amount']
        net_income = float(net_income_series.iloc[0]) if not net_income_series.empty and pd.notna(net_income_series.iloc[0]) else 0
        
        # 자본총계 (재무상태표)
        # '자본총계' 또는 '자본'을 포함하되, '지배기업 소유주지분', '비지배지분' 등을 제외한 순수 자본총계를 찾아야 함
        # 보다 정확한 계정명은 DART XBRL 표준 계정과목 체계 참고 필요
        total_equity_series = financial_df[
            (financial_df['sj_nm'] == '재무상태표') &
            (financial_df['account_nm'].str.contains(r'^(?=.*자본)(?!.*지배)(?!.*비지배).*총계$|자본총계', na=False, regex=True)) 
            # (financial_df['account_nm'].str.contains('자본총계', na=False) | financial_df['account_nm'].str.fullmatch('자본', na=False))
        ]['thstrm_amount']
        if total_equity_series.empty: # 만약 '자본총계'가 없다면 '자본' 항목으로 다시 시도
             total_equity_series = financial_df[
                (financial_df['sj_nm'] == '재무상태표') &
                (financial_df['account_nm'].str.fullmatch('자본', na=False)) # 정확히 '자본'과 일치하는 항목
            ]['thstrm_amount']

        total_equity = float(total_equity_series.iloc[0]) if not total_equity_series.empty and pd.notna(total_equity_series.iloc[0]) else 0

        # 부채총계 (재무상태표)
        total_debt_series = financial_df[
            (financial_df['sj_nm'] == '재무상태표') &
            (financial_df['account_nm'].str.contains('부채총계', na=False) | financial_df['account_nm'].str.fullmatch('부채', na=False))
        ]['thstrm_amount']
        total_debt = float(total_debt_series.iloc[0]) if not total_debt_series.empty and pd.notna(total_debt_series.iloc[0]) else 0

        if total_equity > 0: # 0으로 나누는 것 방지
            roe = (net_income / total_equity) * 100
            debt_ratio = (total_debt / total_equity) * 100
        else: # 자본이 0이거나 음수일 경우
            if net_income > 0: roe = float('inf') # 또는 다른 특정 값
            elif net_income < 0: roe = float('-inf')
            else: roe = 0 # 또는 None/N/A
            
            if total_debt > 0: debt_ratio = float('inf') # 또는 다른 특정 값
            else: debt_ratio = 0 # 또는 None/N/A

        logger.info(f"Calculated - Sales: {sales}, Net Income: {net_income}, Total Equity: {total_equity}, Total Debt: {total_debt}")
        logger.info(f"Calculated ratios - ROE: {roe}, Debt Ratio: {debt_ratio}")

    except Exception as e:
        logger.error(f"Error calculating financial ratios: {e}. Financial DF head:\n{financial_df.head()}")
        # MVP 목업 데이터용 예시 값 (실제 데이터 파싱 실패 시, 이 부분은 실제 API 연동 시 제거하거나 정교하게 수정)
        # DART API에서 'account_nm'은 고정적이지 않을 수 있으므로, 'account_id' (계정ID)를 사용하는 것이 더 안정적일 수 있습니다.
        # 현재는 'account_nm'을 사용하고 있어, 특정 기업/보고서에서 원하는 값을 못 찾을 수 있습니다.
        # 목업 데이터 확인 로직 제거 (실제 데이터 파싱에 집중)
        # if financial_df['account_nm'].iloc[0] == '유동자산': # 목업데이터인지 확인 (이런 방식은 불안정)
        #      roe = 15.0
        #      debt_ratio = 50.0
        #      sales = 1000000000 # 예시 매출액
        #      logger.info(f"Using mock ratios due to calculation error - ROE: {roe}, Debt Ratio: {debt_ratio}")
        # else:
        return {"error": f"Calculation error: {str(e)}"}


    return {
        "ROE (%)": roe,
        "부채비율 (%)": debt_ratio,
        "매출액": sales, # 계산된 sales 값을 직접 사용
        # PER, PBR 등은 현재 주가 정보가 필요하므로, data_fetcher와 연계 필요
    }
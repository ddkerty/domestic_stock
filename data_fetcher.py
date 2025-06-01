import pandas as pd
import requests
import zipfile
import io
import xml.etree.ElementTree as ET
from typing import Optional, Tuple

import config
from utils import timed_cache, get_logger

logger = get_logger(__name__)

# FinanceDataReader 임포트 시도
try:
    import FinanceDataReader as fdr
    FDR_AVAILABLE = True
except ImportError:
    FDR_AVAILABLE = False
    logger.critical("FinanceDataReader 라이브러리를 찾을 수 없습니다. pip install finance-datareader로 설치해주세요.")


@timed_cache(seconds=config.CACHE_TIMEOUT_SECONDS * 24)
def get_corp_code_and_name(stock_code: str) -> Tuple[Optional[str], Optional[str]]:
    # 이 함수는 수정되지 않았습니다.
    # ... (기존 코드와 동일)
    api_key = config.DART_API_KEY
    if not api_key or api_key == "YOUR_DART_API_KEY_HERE":
        logger.error("DART API 키가 config.py에 설정되지 않았습니다.")
        return None, None

    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_filename = "CORPCODE.XML"
            with zf.open(xml_filename) as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                for corp_element in root.findall("list"):
                    corp_code_xml = corp_element.findtext("corp_code")
                    corp_name_xml = corp_element.findtext("corp_name")
                    stock_code_xml = corp_element.findtext("stock_code")
                    if stock_code_xml and stock_code_xml.strip() == stock_code.strip():
                        return corp_code_xml.strip(), corp_name_xml.strip()
        return None, None
    except Exception as e:
        logger.error(f"DART 회사 코드 처리 중 예기치 않은 오류: {e}")
        return None, None

@timed_cache(seconds=config.CACHE_TIMEOUT_SECONDS)
def fetch_dart_financial_data(stock_code: str, year: str, report_code: str = "11014", fs_div: str = "CFS") -> pd.DataFrame:
    # 이 함수는 수정되지 않았습니다.
    # ... (기존 코드와 동일)
    api_key = config.DART_API_KEY
    if not api_key or api_key == "YOUR_DART_API_KEY_HERE":
        logger.warning("DART API 키가 설정되어 있지 않습니다. 재무 데이터를 가져올 수 없습니다.")
        return pd.DataFrame()
    corp_code, _ = get_corp_code_and_name(stock_code)
    if not corp_code:
        return pd.DataFrame()
    url = (
        f"https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
        f"?crtfc_key={api_key}&corp_code={corp_code}&bsns_year={year}&reprt_code={report_code}&fs_div={fs_div}"
    )
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        result = response.json()
        if result.get('status') == '000' and 'list' in result:
            df = pd.DataFrame(result['list'])
            amount_cols = ['thstrm_amount', 'frmtrm_amount', 'bfefrmtrm_amount']
            for col in amount_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce')
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"DART 재무제표 처리 중 예기치 않은 오류: {e}")
        return pd.DataFrame()


@timed_cache(seconds=config.CACHE_TIMEOUT_SECONDS // 4)
def fetch_stock_price_data(stock_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    # 이 함수는 수정되지 않았습니다.
    # ... (기존 코드와 동일)
    if not FDR_AVAILABLE:
        return pd.DataFrame()
    try:
        df = fdr.DataReader(stock_code, start=start_date, end=end_date)
        return df.reset_index()
    except Exception as e:
        logger.error(f"FinanceDataReader로 주가 데이터 조회 중 오류: {e}")
        return pd.DataFrame()


@timed_cache(seconds=config.CACHE_TIMEOUT_SECONDS * 24)
def fetch_company_info(stock_code: str) -> dict:
    # 이 함수는 수정되지 않았습니다.
    # ... (기존 코드와 동일)
    logger.info(f"기업 정보 요청 (DART 우선): {stock_code}")
    corp_code, corp_name_dart = get_corp_code_and_name(stock_code)
    final_corp_name = corp_name_dart

    if not final_corp_name and FDR_AVAILABLE:
        try:
            krx_list = get_krx_stock_list()
            if not krx_list.empty:
                company_row = krx_list[krx_list['Symbol'] == stock_code]
                if not company_row.empty:
                    final_corp_name = company_row['Name'].iloc[0]
        except Exception as e_fdr:
            logger.warning(f"FinanceDataReader로 회사명 조회 중 오류: {e_fdr}")

    if final_corp_name is None:
        final_corp_name = stock_code

    return {'stock_code': stock_code, 'corp_code': corp_code, 'corp_name': final_corp_name}


@timed_cache(seconds=3600 * 24)
def get_krx_stock_list() -> pd.DataFrame:
    """
    KRX 전체 종목 리스트를 반환합니다.
    FinanceDataReader의 컬럼명 변경('Code' -> 'Symbol')에 대응합니다.
    """
    if not FDR_AVAILABLE:
        logger.error("FinanceDataReader가 설치되지 않아 KRX 종목 리스트를 가져올 수 없습니다.")
        return pd.DataFrame(columns=['Symbol', 'Name'])
    
    logger.info("FinanceDataReader를 사용하여 KRX 전체 종목 목록 가져오기 시작...")
    try:
        krx = fdr.StockListing('KRX')
        if krx.empty:
            logger.warning("FinanceDataReader에서 KRX 목록을 가져왔으나 데이터가 비어있습니다.")
            return pd.DataFrame(columns=['Symbol', 'Name'])

        # --- START: 수정된 핵심 로직 ---
        # 1. 변경된 'Code' 컬럼이 있는지 확인
        if 'Code' not in krx.columns or 'Name' not in krx.columns:
            logger.error(f"KRX 목록에 필수 컬럼('Code', 'Name')이 없습니다. 현재 컬럼: {krx.columns}")
            return pd.DataFrame(columns=['Symbol', 'Name'])
        
        # 2. 'Code'와 'Name' 컬럼만 선택하고 결측값 처리
        krx_cleaned = krx[['Code', 'Name']].dropna(subset=['Code', 'Name'])
        
        # 3. 앱 전체 호환성을 위해 'Code' 컬럼명을 'Symbol'로 변경
        krx_cleaned = krx_cleaned.rename(columns={'Code': 'Symbol'})
        # --- END: 수정된 핵심 로직 ---
        
        logger.info(f"KRX에서 {len(krx_cleaned)}개 종목을 성공적으로 가져왔습니다.")
        return krx_cleaned
        
    except Exception as e:
        logger.error(f"KRX 종목 목록을 가져오는 중 심각한 오류가 발생했습니다: {e}", exc_info=True)
        return pd.DataFrame(columns=['Symbol', 'Name'])
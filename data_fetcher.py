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
    """DART API로부터 기업 고유번호와 회사명을 가져옵니다. ZIP 파일 내부의 XML 파일명을 동적으로 찾도록 수정되었습니다."""
    api_key = config.DART_API_KEY
    if not api_key or api_key == "YOUR_DART_API_KEY_HERE":
        logger.error("DART API 키가 config.py에 설정되지 않았습니다.")
        return None, None

    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key}"
    logger.info(f"DART: 전체 기업 고유번호 목록 다운로드 요청...")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            # --- START: 수정된 핵심 로직 ---
            # 특정 파일명('CORPCODE.XML')을 하드코딩하는 대신, 압축파일 내의 첫 번째 .xml 파일을 동적으로 찾습니다.
            xml_filename = None
            for name in zf.namelist():
                if name.lower().endswith('.xml'):
                    xml_filename = name
                    logger.info(f"DART 응답 ZIP 파일에서 '{xml_filename}'을 발견했습니다.")
                    break
            
            if not xml_filename:
                logger.error("DART 응답 ZIP 파일에서 XML 파일을 찾을 수 없습니다.")
                return None, None
            # --- END: 수정된 핵심 로직 ---

            with zf.open(xml_filename) as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                for corp_element in root.findall("list"):
                    corp_code_xml = corp_element.findtext("corp_code")
                    corp_name_xml = corp_element.findtext("corp_name")
                    stock_code_xml = corp_element.findtext("stock_code")
                    if stock_code_xml and stock_code_xml.strip() == stock_code.strip():
                        logger.info(f"DART: Stock Code {stock_code}에 해당하는 기업코드({corp_code_xml})를 찾았습니다.")
                        return corp_code_xml.strip(), corp_name_xml.strip()

        logger.warning(f"DART: Stock Code {stock_code}에 해당하는 회사 코드를 전체 목록에서 찾지 못했습니다.")
        return None, None
    except requests.exceptions.RequestException as e:
        logger.error(f"DART 회사 코드 목록 요청 실패: {e}")
        return None, None
    except Exception as e:
        logger.error(f"DART 회사 코드 처리 중 예기치 않은 오류: {e}", exc_info=True)
        return None, None


@timed_cache(seconds=config.CACHE_TIMEOUT_SECONDS)
def fetch_dart_financial_data(stock_code: str, year: str, report_code: str = "11014", fs_div: str = "CFS") -> Tuple[pd.DataFrame, str]:
    """DART 재무 데이터를 가져옵니다. 성공 시 (데이터프레임, "Success"), 실패 시 (빈 데이터프레임, "실패 메시지")를 반환합니다."""
    api_key = config.DART_API_KEY
    if not api_key or api_key == "YOUR_DART_API_KEY_HERE":
        msg = "DART API 키가 설정되지 않았습니다."
        logger.warning(msg)
        return pd.DataFrame(), msg

    corp_code, _ = get_corp_code_and_name(stock_code)
    if not corp_code:
        msg = f"DART 고유 기업 코드를 찾을 수 없습니다. 코넥스, 스팩(SPAC), 일부 신규 상장 종목은 재무 정보 조회가 지원되지 않을 수 있습니다."
        logger.error(f"DART: {stock_code}에 대한 회사 코드를 찾지 못해 재무제표를 요청할 수 없습니다.")
        return pd.DataFrame(), msg
        
    url = (
        f"https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
        f"?crtfc_key={api_key}&corp_code={corp_code}&bsns_year={year}&reprt_code={report_code}&fs_div={fs_div}"
    )
    logger.info(f"DART: 재무제표 요청 - URL: {url.replace(api_key, '******')}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        result = response.json()
        status = result.get('status')
        message = result.get('message')

        if status == '000':
            if 'list' in result and result['list']:
                df = pd.DataFrame(result['list'])
                amount_cols = ['thstrm_amount', 'frmtrm_amount', 'bfefrmtrm_amount']
                for col in amount_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce')
                return df, "Success"
            else:
                return pd.DataFrame(), f"DART에 해당 조건의 데이터가 없습니다 (Status: {status})."
        elif status == '013':
             return pd.DataFrame(), f"DART에 해당 기간({year}년)의 사업보고서 데이터가 없습니다. (Status: {status})"
        else:
            return pd.DataFrame(), f"DART API 오류가 발생했습니다. (Status: {status}, Message: {message})"
            
    except requests.exceptions.RequestException as e:
        msg = f"DART API 요청 실패: 네트워크 연결을 확인해주세요. ({e})"
        logger.error(msg)
        return pd.DataFrame(), msg
    except ValueError as e: # JSON 파싱 오류
        msg = f"DART API 응답을 처리할 수 없습니다. (JSON 파싱 오류: {e})"
        logger.error(f"{msg} 응답 내용: {response.text[:200]}")
        return pd.DataFrame(), msg
    except Exception as e:
        msg = f"재무제표 처리 중 예기치 않은 오류가 발생했습니다: {e}"
        logger.error(msg)
        return pd.DataFrame(), msg

# 나머지 함수들은 수정되지 않았습니다.
@timed_cache(seconds=config.CACHE_TIMEOUT_SECONDS // 4)
def fetch_stock_price_data(stock_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
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
    if not FDR_AVAILABLE:
        logger.error("FinanceDataReader가 설치되지 않아 KRX 종목 리스트를 가져올 수 없습니다.")
        return pd.DataFrame(columns=['Symbol', 'Name'])
    
    logger.info("FinanceDataReader를 사용하여 KRX 전체 종목 목록 가져오기 시작...")
    try:
        krx = fdr.StockListing('KRX')
        if krx.empty:
            logger.warning("FinanceDataReader에서 KRX 목록을 가져왔으나 데이터가 비어있습니다.")
            return pd.DataFrame(columns=['Symbol', 'Name'])

        if 'Code' not in krx.columns or 'Name' not in krx.columns:
            logger.error(f"KRX 목록에 필수 컬럼('Code', 'Name')이 없습니다. 현재 컬럼: {krx.columns}")
            return pd.DataFrame(columns=['Symbol', 'Name'])
        
        krx_cleaned = krx[['Code', 'Name']].dropna(subset=['Code', 'Name'])
        krx_cleaned = krx_cleaned.rename(columns={'Code': 'Symbol'})
        
        logger.info(f"KRX에서 {len(krx_cleaned)}개 종목을 성공적으로 가져왔습니다.")
        return krx_cleaned
        
    except Exception as e:
        logger.error(f"KRX 종목 목록을 가져오는 중 심각한 오류가 발생했습니다: {e}", exc_info=True)
        return pd.DataFrame(columns=['Symbol', 'Name'])

import pandas as pd
import requests
import zipfile
import io
import xml.etree.ElementTree as ET

import config
from utils import timed_cache, get_logger

logger = get_logger(__name__)

# FinanceDataReader 임포트 시도
try:
    import FinanceDataReader as fdr
    FDR_AVAILABLE = True
except ImportError:
    FDR_AVAILABLE = False
    logger.warning("FinanceDataReader 라이브러리를 찾을 수 없습니다. pip install finance-datareader로 설치해주세요. 주가 데이터 및 KRX 목록은 목업으로 대체됩니다.")


@timed_cache(seconds=config.CACHE_TIMEOUT_SECONDS * 24)
def get_corp_code_and_name(stock_code: str) -> tuple[str | None, str | None]:
    api_key = config.DART_API_KEY
    if not api_key or api_key == "YOUR_DART_API_KEY_HERE":
        logger.error("DART API 키가 config.py에 설정되지 않았습니다.")
        return None, None

    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key}"
    logger.info(f"DART: 회사 코드 및 이름 목록 요청 (stock_code: {stock_code})")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_filename = None
            for name in zf.namelist():
                if name.upper() == "CORPCODE.XML":
                    xml_filename = name
                    break
            if not xml_filename:
                logger.error("CORPCODE.xml 파일을 zip 아카이브에서 찾을 수 없습니다.")
                return None, None
            with zf.open(xml_filename) as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                for corp_element in root.findall("list"):
                    corp_code_xml = corp_element.findtext("corp_code")
                    corp_name_xml = corp_element.findtext("corp_name")
                    stock_code_xml = corp_element.findtext("stock_code")
                    if stock_code_xml and stock_code_xml.strip() == stock_code.strip():
                        logger.info(f"DART: 회사 코드 찾음 - Code: {corp_code_xml}, Name: {corp_name_xml} for Stock Code: {stock_code}")
                        return corp_code_xml.strip(), corp_name_xml.strip()
        logger.warning(f"DART: Stock Code {stock_code}에 해당하는 회사 코드를 찾지 못했습니다.")
        return None, None
    except requests.exceptions.RequestException as e:
        logger.error(f"DART 회사 코드 목록 요청 실패: {e}")
        return None, None
    except zipfile.BadZipFile:
        logger.error("DART 회사 코드 응답이 유효한 ZIP 파일이 아닙니다.")
        return None, None
    except ET.ParseError:
        logger.error("DART 회사 코드 XML 파싱 오류.")
        return None, None
    except Exception as e:
        logger.error(f"DART 회사 코드 처리 중 예기치 않은 오류: {e}")
        return None, None

@timed_cache(seconds=config.CACHE_TIMEOUT_SECONDS)
def fetch_dart_financial_data(stock_code: str, year: str, report_code: str = "11014", fs_div: str = "CFS") -> pd.DataFrame:
    api_key = config.DART_API_KEY
    if not api_key or api_key == "YOUR_DART_API_KEY_HERE":
        logger.warning("DART API 키가 설정되어 있지 않습니다. 재무 데이터를 가져올 수 없습니다.")
        return pd.DataFrame()
    corp_code, _ = get_corp_code_and_name(stock_code)
    if not corp_code:
        logger.error(f"DART: {stock_code}에 대한 회사 코드를 찾지 못해 재무제표를 요청할 수 없습니다.")
        return pd.DataFrame()
    url = (
        f"https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
        f"?crtfc_key={api_key}&corp_code={corp_code}&bsns_year={year}&reprt_code={report_code}&fs_div={fs_div}"
    )
    logger.info(f"DART: 재무제표 요청 - URL: {url.replace(api_key, '******')}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        result = response.json()
        if result.get('status') == '000':
            if 'list' in result and result['list']:
                df = pd.DataFrame(result['list'])
                logger.info(f"DART: 재무제표 {len(df)}건 수신 완료 (Stock: {stock_code}, Year: {year}, Report: {report_code}, FS: {fs_div})")
                amount_cols = ['thstrm_amount', 'frmtrm_amount', 'bfefrmtrm_amount']
                for col in amount_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce')
                return df
            else:
                logger.warning(f"DART: 재무제표 데이터가 없습니다 (status 000, but no list).")
                return pd.DataFrame()
        elif result.get('status') == '013':
            logger.warning(f"DART: 해당 조건의 재무제표 데이터가 없습니다 (status 013). 메시지: {result.get('message')}")
            return pd.DataFrame()
        else:
            logger.error(f"DART API 오류: Status {result.get('status')}, Message: {result.get('message')}")
            return pd.DataFrame()
    except requests.exceptions.Timeout:
        logger.error(f"DART API 요청 시간 초과 (Stock: {stock_code})")
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        logger.error(f"DART API 요청 실패: {e} (Stock: {stock_code})")
        return pd.DataFrame()
    except ValueError as e:
        logger.error(f"DART API 응답 JSON 파싱 오류: {e}. 응답 내용: {response.text[:200]}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"DART 재무제표 처리 중 예기치 않은 오류: {e}")
        return pd.DataFrame()

@timed_cache(seconds=config.CACHE_TIMEOUT_SECONDS // 4)
def fetch_stock_price_data(stock_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    logger.info(f"주가 데이터 요청: {stock_code} (기간: {start_date} ~ {end_date})")
    if not FDR_AVAILABLE:
        logger.warning("FinanceDataReader가 설치되지 않아 주가 데이터를 가져올 수 없습니다.")
        return pd.DataFrame()
    try:
        df = fdr.DataReader(stock_code, start_date, end_date)
        if df.empty:
            logger.warning(f"주가 데이터 없음: {stock_code} (기간: {start_date} ~ {end_date})")
            return pd.DataFrame()
        df = df.reset_index()
        logger.info(f"주가 데이터 수신 완료: {stock_code}, {len(df)} 행")
        return df
    except Exception as e:
        logger.error(f"{stock_code} 주가 데이터 조회 오류: {e}")
        return pd.DataFrame()

@timed_cache(seconds=config.CACHE_TIMEOUT_SECONDS * 24)
def fetch_company_info(stock_code: str) -> dict:
    logger.info(f"기업 정보 요청 (DART): {stock_code}")
    corp_code, corp_name = get_corp_code_and_name(stock_code)
    if corp_name and corp_code:
        return {'stock_code': stock_code, 'corp_code': corp_code, 'corp_name': corp_name}
    else:
        logger.warning(f"{stock_code}에 대한 기업명을 DART에서 가져오지 못했습니다. FDR 목록에서 시도합니다.")
        if FDR_AVAILABLE:
            try:
                krx_list = get_krx_stock_list() # 캐시된 목록 사용
                if not krx_list.empty:
                    company_row = krx_list[krx_list['Symbol'] == stock_code]
                    if not company_row.empty:
                        corp_name_fdr = company_row['Name'].iloc[0]
                        logger.info(f"FinanceDataReader에서 회사명 조회 성공: {corp_name_fdr}")
                        return {'stock_code': stock_code, 'corp_code': None, 'corp_name': corp_name_fdr}
            except Exception as e_fdr:
                logger.warning(f"FinanceDataReader로 회사명 조회 중 오류: {e_fdr}")
        return {'stock_code': stock_code, 'corp_code': None, 'corp_name': f"기업({stock_code})"}


@timed_cache(seconds=3600 * 24) # 하루 캐시
def get_krx_stock_list() -> pd.DataFrame:
    """KRX 전체 종목 리스트 (종목명, 종목코드)를 반환합니다."""
    logger.info("Fetching KRX stock list...")
    if not FDR_AVAILABLE:
        logger.warning("FinanceDataReader가 설치되지 않아 KRX 종목 리스트를 가져올 수 없습니다.")
        return pd.DataFrame(columns=['Symbol', 'Name']) # 빈 DataFrame에 컬럼명 명시
    try:
        # KRX, KOSPI, KOSDAQ, KONEX 등
        krx = fdr.StockListing('KRX') # 전체 시장
        # 일반적인 주식 외 상품 제외 (선택적)
        # 아래 필터는 예시이며, 필요에 따라 조정
        # krx = krx[~krx['Name'].str.contains('스팩|제[0-9]+호|리츠|ETF|ETN|선물|옵션|인버스|레버리지', case=False, na=False)]
        # krx = krx[krx['Market'].isin(['KOSPI', 'KOSDAQ'])] # 코스피, 코스닥만 필터링
        
        if krx.empty:
            logger.warning("FinanceDataReader에서 KRX 목록을 가져왔으나 비어있습니다.")
            return pd.DataFrame(columns=['Symbol', 'Name'])

        logger.info(f"Fetched {len(krx)} stocks from KRX.")
        return krx[['Symbol', 'Name']].dropna(subset=['Symbol', 'Name']) # Symbol, Name이 NaN인 경우 제거
    except Exception as e:
        logger.error(f"Error fetching KRX stock list: {e}")
        return pd.DataFrame(columns=['Symbol', 'Name'])
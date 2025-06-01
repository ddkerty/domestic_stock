
import pandas as pd
import requests
import zipfile
import io # io 모듈 임포트
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
    """
    네이버 금융에서 주가 데이터를 크롤링하여 반환합니다.
    """
    try:
        logger.info(f"네이버 시세 요청 시작: {stock_code}, 기간: {start_date} ~ {end_date}")
        base_url = f"https://finance.naver.com/item/sise_day.nhn?code={stock_code}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'} # 좀 더 일반적인 User-Agent
        dfs = []
        
        # 네이버 금융은 한 페이지에 10개 거래일 표시
        # 요청 기간에 따라 필요한 페이지 수 계산 (대략적으로)
        # 여기서는 최대 10페이지 (약 100 거래일)로 제한
        max_pages_to_fetch = 10 
        if start_date and end_date:
            try:
                s_date = pd.to_datetime(start_date)
                e_date = pd.to_datetime(end_date)
                # 대략적인 거래일 수 (주말 제외, 공휴일 미고려)
                business_days = pd.bdate_range(s_date, e_date)
                num_days_needed = len(business_days)
                max_pages_to_fetch = (num_days_needed // 10) + 2 # 필요한 페이지 수 + 여유분
                if max_pages_to_fetch > 30 : max_pages_to_fetch = 30 # 과도한 요청 방지 (최대 300 거래일)
                logger.info(f"필요 예상 페이지 수: {max_pages_to_fetch-2}, 실제 요청 페이지 수: {max_pages_to_fetch}")
            except Exception:
                pass # 날짜 파싱 실패 시 기본값 사용


        for page in range(1, max_pages_to_fetch + 1): 
            url = f"{base_url}&page={page}"
            res = requests.get(url, headers=headers, timeout=5) # 타임아웃 추가
            res.raise_for_status() # HTTP 오류 발생 시 예외

            # FutureWarning 해결: io.StringIO 사용
            html_content = io.StringIO(res.text)
            tables = pd.read_html(html_content)

            if not tables or len(tables) == 0:
                logger.warning(f"페이지 {page}에서 테이블을 찾을 수 없습니다.")
                if page == 1: # 첫 페이지부터 데이터가 없으면 중단
                    return pd.DataFrame()
                break # 데이터가 더 이상 없으면 중단

            df_page = tables[0]
            if df_page.empty or df_page.shape[1] < 7: # 컬럼 개수 등으로 유효성 검사
                logger.warning(f"페이지 {page}의 테이블 형식이 예상과 다릅니다: {df_page.head()}")
                if page == 1: return pd.DataFrame()
                break
            
            # NaN 행 제거 (보통 페이지 마지막에 빈 행이 있음)
            df_page = df_page.dropna(how='all') 
            if df_page.iloc[:, 0].isnull().all(): # 첫 번째 열이 모두 NaN이면 유효한 데이터가 없는 것으로 간주
                 logger.info(f"페이지 {page}에 더 이상 유효한 데이터가 없습니다.")
                 break

            dfs.append(df_page)
            
            # 현재 페이지의 마지막 날짜가 start_date보다 이전이면 더 이상 가져올 필요 없음 (선택적 최적화)
            try:
                last_date_on_page_str = df_page.iloc[-1, 0]
                last_date_on_page = pd.to_datetime(last_date_on_page_str, format='%Y.%m.%d')
                if start_date and last_date_on_page < pd.to_datetime(start_date):
                    logger.info(f"페이지 {page}의 마지막 날짜({last_date_on_page_str})가 시작 날짜({start_date}) 이전이므로 중단합니다.")
                    break
            except Exception as date_e:
                logger.warning(f"페이지 {page} 날짜 파싱 중 오류: {date_e}")


        if not dfs:
            logger.warning(f"{stock_code}에 대한 주가 데이터를 가져오지 못했습니다 (dfs 비어있음).")
            return pd.DataFrame()

        df_all = pd.concat(dfs, ignore_index=True)
        df_all = df_all.dropna(subset=[df_all.columns[0]]) # 첫 번째 열(날짜) 기준으로 NaN 제거
        df_all.columns = ['Date', 'Close', 'Diff', 'Open', 'High', 'Low', 'Volume'] # 컬럼명 재확인 및 설정
        
        # 중복된 날짜 제거 (가장 처음 나온 데이터 유지)
        df_all = df_all.drop_duplicates(subset=['Date'], keep='first')

        df_all['Date'] = pd.to_datetime(df_all['Date'], format='%Y.%m.%d')
        df_all = df_all.sort_values('Date', ascending=True)

        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df_all[col] = pd.to_numeric(df_all[col].astype(str).str.replace(',', ''), errors='coerce')

        # 최종적으로 날짜 필터링
        if start_date:
            df_all = df_all[df_all['Date'] >= pd.to_datetime(start_date)]
        if end_date:
            df_all = df_all[df_all['Date'] <= pd.to_datetime(end_date)]

        logger.info(f"네이버 시세 수집 완료: {len(df_all)}건")
        return df_all[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].reset_index(drop=True)

    except requests.exceptions.RequestException as req_e:
        logger.error(f"네이버 시세 요청 중 네트워크 오류: {req_e} (URL: {url if 'url' in locals() else 'N/A'})")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"네이버 시세 크롤링 중 예외 발생: {e}")
        return pd.DataFrame()


@timed_cache(seconds=config.CACHE_TIMEOUT_SECONDS * 24)
def fetch_company_info(stock_code: str) -> dict:
    logger.info(f"기업 정보 요청 (DART 우선): {stock_code}")
    corp_code, corp_name_dart = get_corp_code_and_name(stock_code) # DART에서 corp_code와 함께 이름 가져옴
    
    final_corp_name = None

    if corp_name_dart: # DART에서 이름을 가져왔다면 우선 사용
        final_corp_name = corp_name_dart
        logger.info(f"DART에서 기업명 조회: {final_corp_name}")
    else: # DART에서 못 가져왔다면 FDR 시도
        logger.warning(f"{stock_code}에 대한 기업명을 DART에서 가져오지 못했습니다. FDR 목록에서 시도합니다.")
        if FDR_AVAILABLE:
            try:
                krx_list = get_krx_stock_list() 
                if not krx_list.empty:
                    company_row = krx_list[krx_list['Symbol'] == stock_code]
                    if not company_row.empty:
                        corp_name_fdr = company_row['Name'].iloc[0]
                        final_corp_name = corp_name_fdr
                        logger.info(f"FinanceDataReader에서 회사명 조회 성공: {final_corp_name}")
            except Exception as e_fdr:
                logger.warning(f"FinanceDataReader로 회사명 조회 중 오류: {e_fdr}")

    if final_corp_name is None: # DART와 FDR 모두 실패 시
        logger.warning(f"DART 및 FDR에서 {stock_code}의 기업명을 찾지 못했습니다.")
        final_corp_name = stock_code # 종목 코드를 이름으로 사용

    return {'stock_code': stock_code, 'corp_code': corp_code, 'corp_name': final_corp_name}


@timed_cache(seconds=3600 * 24) # 하루 캐시
def get_krx_stock_list() -> pd.DataFrame:
    """KRX 전체 종목 리스트 (종목명, 종목코드)를 반환합니다."""
    if not FDR_AVAILABLE:
        logger.error("FinanceDataReader가 설치되지 않아 KRX 종목 리스트를 가져올 수 없습니다.")
        return pd.DataFrame(columns=['Symbol', 'Name'])
    
    logger.info("FinanceDataReader를 사용하여 KRX 전체 종목 목록 가져오기 시작...")
    try:
        krx = fdr.StockListing('KRX')
        if krx.empty:
            logger.warning("FinanceDataReader에서 KRX 목록을 가져왔으나 데이터가 비어있습니다. 네트워크 문제나 API 변경일 수 있습니다.")
            return pd.DataFrame(columns=['Symbol', 'Name'])

        # 필수 컬럼 확인
        if 'Symbol' not in krx.columns or 'Name' not in krx.columns:
            logger.error(f"KRX 목록에 필수 컬럼('Symbol', 'Name')이 없습니다. 현재 컬럼: {krx.columns}")
            return pd.DataFrame(columns=['Symbol', 'Name'])
        
        # 결측값 처리
        krx_cleaned = krx[['Symbol', 'Name']].dropna(subset=['Symbol', 'Name'])
        
        logger.info(f"KRX에서 {len(krx_cleaned)}개 종목을 성공적으로 가져왔습니다.")
        return krx_cleaned
        
    except Exception as e:
        logger.error(f"KRX 종목 목록을 가져오는 중 심각한 오류가 발생했습니다: {e}", exc_info=True)
        return pd.DataFrame(columns=['Symbol', 'Name'])

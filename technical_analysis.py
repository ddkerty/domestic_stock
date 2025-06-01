import pandas as pd
import numpy as np
from utils import get_logger

logger = get_logger(__name__)

def calculate_technical_indicators(price_df: pd.DataFrame):
    """
    주가 데이터를 기반으로 기술적 지표를 계산합니다.
    TA-Lib 없이 pandas로 모든 지표를 구현합니다.
    """
    logger.info("Calculating enhanced technical indicators...")
    
    if price_df.empty or 'Close' not in price_df.columns:
        logger.warning("Price data is empty or 'Close' column is missing.")
        return price_df
    
    # 기존 이동평균선 (유지)
    if len(price_df['Close']) >= 5:
        price_df['SMA_5'] = price_df['Close'].rolling(window=5).mean()
    else:
        price_df['SMA_5'] = None
        
    if len(price_df['Close']) >= 20:
        price_df['SMA_20'] = price_df['Close'].rolling(window=20).mean()
    else:
        price_df['SMA_20'] = None
    
    # EMA 계산 (MACD에 필요)
    price_df['EMA_12'] = price_df['Close'].ewm(span=12, adjust=False).mean()
    price_df['EMA_26'] = price_df['Close'].ewm(span=26, adjust=False).mean()
    
    # MACD 계산
    price_df['MACD'] = price_df['EMA_12'] - price_df['EMA_26']
    price_df['MACD_signal'] = price_df['MACD'].ewm(span=9, adjust=False).mean()
    price_df['MACD_hist'] = price_df['MACD'] - price_df['MACD_signal']
    
    # RSI 계산
    price_df = calculate_rsi(price_df, period=14)
    
    # 볼린저 밴드 추가
    price_df = calculate_bollinger_bands(price_df, period=20, std_dev=2)
    
    # VWAP (기존 유지)
    if all(col in price_df.columns for col in ['High', 'Low', 'Close']):
        price_df['VWAP_daily_approx'] = (price_df['High'] + price_df['Low'] + price_df['Close']) / 3
    
    logger.info("Enhanced technical indicators calculated successfully")
    return price_df

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """RSI(Relative Strength Index) 계산"""
    if 'Close' not in df.columns:
        logger.warning("RSI 계산을 위해 'Close' 컬럼이 필요합니다.")
        return df
    
    delta = df['Close'].diff()
    gain = delta.whe

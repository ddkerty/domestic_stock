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
    
    df = price_df.copy() # 원본 데이터프레임 수정을 피하기 위해 복사본 사용

    # 이동평균선
    if len(df['Close']) >= 5:
        df['SMA_5'] = df['Close'].rolling(window=5).mean()
    else:
        df['SMA_5'] = np.nan
        
    if len(df['Close']) >= 20:
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
    else:
        df['SMA_20'] = np.nan
    
    # EMA 계산 (MACD에 필요)
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    
    # MACD 계산
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    
    # RSI 계산
    df = calculate_rsi(df, period=14)
    
    # 볼린저 밴드 추가
    df = calculate_bollinger_bands(df, period=20, std_dev=2)
    
    logger.info("Enhanced technical indicators calculated successfully")
    return df

def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
    """볼린저 밴드 계산"""
    if f'SMA_{period}' not in df.columns:
        df[f'SMA_{period}'] = df['Close'].rolling(window=period).mean()
    
    std = df['Close'].rolling(window=period).std()
    df['Bollinger_Upper'] = df[f'SMA_{period}'] + (std * std_dev)
    df['Bollinger_Lower'] = df[f'SMA_{period}'] - (std * std_dev)
    return df


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """RSI(Relative Strength Index) 계산"""
    if 'Close' not in df.columns:
        logger.warning("RSI 계산을 위해 'Close' 컬럼이 필요합니다.")
        df['RSI'] = np.nan
        return df
    
    delta = df['Close'].diff()
    
    # --- START: 수정된 라인 ---
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    # --- END: 수정된 라인 ---

    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    # avg_loss가 0이 되는 경우를 방지 (RSI가 100이 됨)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(100) # avg_loss가 0이었던 경우 100으로 채움
    
    return df
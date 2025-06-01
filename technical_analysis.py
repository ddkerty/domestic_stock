import pandas as pd
import numpy as np
from utils import get_logger
from typing import Tuple, Dict

logger = get_logger(__name__)

def calculate_fibonacci_retracement(df: pd.DataFrame) -> Dict[str, float]:
    """피보나치 되돌림 레벨을 계산합니다."""
    if df.empty:
        return {}
    
    highest_high = df['High'].max()
    lowest_low = df['Low'].min()
    price_range = highest_high - lowest_low
    
    if price_range == 0:
        return {}
        
    levels = {
        'level_0.0': highest_high,
        'level_23.6': highest_high - (price_range * 0.236),
        'level_38.2': highest_high - (price_range * 0.382),
        'level_50.0': highest_high - (price_range * 0.5),
        'level_61.8': highest_high - (price_range * 0.618),
        'level_78.6': highest_high - (price_range * 0.786),
        'level_100.0': lowest_low,
    }
    return levels

def calculate_technical_indicators(price_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """모든 기술적 지표와 피보나치 레벨을 계산하여 반환합니다."""
    logger.info("Calculating comprehensive technical indicators...")
    
    if price_df.empty or 'Close' not in price_df.columns:
        return price_df, {}
    
    df = price_df.copy()

    # 이동평균선
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    
    # 볼린저 밴드
    df['Upper'] = df['SMA_20'] + (df['Close'].rolling(window=20).std() * 2)
    df['Lower'] = df['SMA_20'] - (df['Close'].rolling(window=20).std() * 2)
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    
    # VWAP (Volume Weighted Average Price)
    if 'Volume' in df.columns:
        vwap_numerator = (df['Close'] * df['Volume']).cumsum()
        vwap_denominator = df['Volume'].cumsum()
        df['VWAP'] = vwap_numerator / vwap_denominator
    
    # 피보나치 레벨 계산
    fib_levels = calculate_fibonacci_retracement(df)

    logger.info("Comprehensive technical indicators calculated successfully.")
    return df, fib_levels
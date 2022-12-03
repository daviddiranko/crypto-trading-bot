import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd


def sma(data: pd.Series, window: int, new_col: str = 'sma') -> pd.Series:
    '''
    Calculate simple moving average for a pandas Series.
    
    Parameters
    ----------
    data: pandas.Series
        series to compute sma of.
    window: int
        rolling window for the sma.
    
    new_col: str
        name of the new series. Default = 'sma'
    
    Returns
    -------
    sma: pd.Series
        sma of data with rolling window 
    '''
    sma = data.rolling(window).mean()
    sma.name = '{}_{}'.format(new_col, window)
    return sma


def get_highs(candles: pd.Series, min_int: int) -> pd.Series:
    '''
    Return highs of candles.
    Highs are defined of points with lower min_int successors and predecessors.
    '''
    highs = candles.loc[candles == candles.rolling(window=2 * min_int,
                                                   center=True).max()]

    recent_high = candles.iloc[-(min_int - 1):].max()
    recent_high_idx = candles.iloc[-(min_int - 1):].idxmax()

    # if maximum of last min_int-1 candles is higher than last high append to highs for a lack of recent history
    if recent_high > highs.iloc[-1]:
        highs.loc[recent_high_idx] = recent_high
    return highs

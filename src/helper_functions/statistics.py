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

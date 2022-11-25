from typing import Dict, Any
from src.TradingModel import TradingModel


def mock_model(model: TradingModel) -> Dict[str, Any]:
    '''
    mock function that opens or closes a BTCUSDT position for testing purposes only.
    '''
    if model.model_args['open'] and not model.model_storage['open']:
        order = model.account.place_order(symbol='BTCUSDT',
                                          order_type='Market',
                                          side='Buy',
                                          qty=0.001)
        model.model_storage['open'] = True
        model.model_args['open'] = False
        return order
    elif not model.model_args['open'] and not model.model_storage['close']:
        reduce_only = model.model_args['reduce_only']
        order = model.account.place_order(symbol='BTCUSDT',
                                          order_type='Market',
                                          side='Sell',
                                          qty=10,
                                          reduce_only=reduce_only)
        model.model_storage['close'] = True
        model.model_args['open'] = True
        return order
    else:
        return None

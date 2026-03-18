"""
pygnx Endpoints
------------------------

Endpoints match Bingx API documentation.
Formatting is: {name: tuple(method, auth, ratelimit, endpoint), ...}.
Name is: (lowercase method)_(2nd last path)_(last path)

Documentation can be found at
https://github.com/APF20/pygnx

:copyright: (c) 2023 APF20

:license: MIT License

:updated: Jun 22, 2024
"""

class Endpoints:

    # Refer: https://bingx-api.github.io/docs/#/swapV2/introduce
    usd_futures = {
        # market - public
        'get_quote_contracts':      ('GET',  False, 10, '/openApi/swap/v2/quote/contracts'),
        'get_quote_price':          ('GET',  False, 10, '/openApi/swap/v2/quote/price'),
        'get_quote_depth':          ('GET',  False, 10, '/openApi/swap/v2/quote/depth'),        # BROKEN-INVALID ASKS
        'get_quote_trades':         ('GET',  False, 10, '/openApi/swap/v2/quote/trades'),
        'get_quote_premiumIndex':   ('GET',  False, 10, '/openApi/swap/v2/quote/premiumIndex'),
        'get_quote_fundingRate':    ('GET',  False, 10, '/openApi/swap/v2/quote/fundingRate'),
        'get_quote_klines':         ('GET',  False, 10, '/openApi/swap/v3/quote/klines'),
        'get_quote_openInterest':   ('GET',  False, 10, '/openApi/swap/v2/quote/openInterest'),
        'get_quote_ticker':         ('GET',  False, 10, '/openApi/swap/v2/quote/ticker'),
        'get_market_historicalTrades':  ('GET',  False, 10, '/openApi/swap/v1/market/historicalTrades'),
        'get_quote_bookTicker':     ('GET',  False, 10, '/openApi/swap/v2/quote/bookTicker'),
        'get_market_markPriceKlines':   ('GET',  False, 10, '/openApi/swap/v1/market/markPriceKlines'),
        'get_ticker_price':         ('GET',  False, 10, '/openApi/swap/v1/ticker/price'),
        # account - private
        'get_user_balance':         ('GET',  True,  5,  '/openApi/swap/v2/user/balance'),
        'get_user_positions':       ('GET',  True,  5,  '/openApi/swap/v2/user/positions'),
        'get_user_income':          ('GET',  True,  5,  '/openApi/swap/v2/user/income'),
        'get_income_export':        ('GET',  True,  5,  '/openApi/swap/v2/user/income/export'),
        'get_user_commissionRate':  ('GET',  True,  5,  '/openApi/swap/v2/user/commissionRate'),
        # trade - private
        'post_order_test':          ('POST', True,  5,  '/openApi/swap/v2/trade/order/test'),
        'post_trade_order':         ('POST', True,  5,  '/openApi/swap/v2/trade/order'),
        'post_trade_batchOrders':   ('POST', True,  5,  '/openApi/swap/v2/trade/batchOrders'),
        'post_trade_closeAllPositions': ('POST', True, 5,   '/openApi/swap/v2/trade/closeAllPositions'),
        'delete_trade_order':       ('DELETE',  True,  5,   '/openApi/swap/v2/trade/order'),
        'delete_trade_batchOrders': ('DELETE',  True,  5,   '/openApi/swap/v2/trade/batchOrders'),
        'delete_trade_allOpenOrders':   ('DELETE',  True, 5, '/openApi/swap/v2/trade/allOpenOrders'),
        'get_trade_openOrders':     ('GET',  True,  5,  '/openApi/swap/v2/trade/openOrders'),     # BROKEN-NO CLORDID
        'get_trade_openOrder':      ('GET',  True,  5,  '/openApi/swap/v2/trade/openOrder'),
        'get_trade_order':          ('GET',  True,  5,  '/openApi/swap/v2/trade/order'),
        'get_trade_marginType':     ('GET',  True,  2,  '/openApi/swap/v2/trade/marginType'),
        'post_trade_marginType':    ('POST', True,  2,  '/openApi/swap/v2/trade/marginType'),
        'get_trade_leverage':       ('GET',  True,  5,  '/openApi/swap/v2/trade/leverage'),
        'post_trade_leverage':      ('POST', True,  2,  '/openApi/swap/v2/trade/leverage'),
        'get_trade_forceOrders':    ('GET',  True,  10, '/openApi/swap/v2/trade/forceOrders'),
        'get_trade_allOrders':      ('GET',  True,  5,  '/openApi/swap/v2/trade/allOrders'),
        'post_trade_positionMargin':('POST', True,  2,  '/openApi/swap/v2/trade/positionMargin'),
        'get_trade_allFillOrders':  ('GET',  True,  5,  '/openApi/swap/v2/trade/allFillOrders'),
        'post_positionSide_dual':   ('POST', True,  2,  '/openApi/swap/v1/positionSide/dual'),
        'get_positionSide_dual':    ('GET',  True,  2,  '/openApi/swap/v1/positionSide/dual'),
        'post_trade_cancelReplace': ('POST', True,  5,  '/openApi/swap/v1/trade/cancelReplace'),
        'post_trade_batchCancelReplace':('POST', True, 2,   '/openApi/swap/v1/trade/batchCancelReplace'),
        'post_trade_cancelAllAfter':('POST', True,  2,  '/openApi/swap/v2/trade/cancelAllAfter'),
        'post_trade_closePosition': ('POST', True,  5,  '/openApi/swap/v1/trade/closePosition'),
        'get_trade_fullOrder':      ('GET',  True,  5,  '/openApi/swap/v1/trade/fullOrder'),     # BROKEN-NO CLORDID
        'get_v1_maintMarginRatio':  ('GET',  True,  5,  '/openApi/swap/v1/maintMarginRatio'),
        'get_trade_fillHistory':    ('GET',  True,  5,  '/openApi/swap/v1/trade/fillHistory'),
        'get_trade_positionHistory':('GET',  True,  5,  '/openApi/swap/v1/trade/positionHistory')
    }

    coin_futures = {
    }

    # Refer: https://bingx-api.github.io/docs/#/en-us/spot/changelog
    spot = {
        # market - public
        'get_common_symbols':       ('GET',  False, 10, '/openApi/spot/v1/common/symbols'),
        'get_market_trades':        ('GET',  False, 10, '/openApi/spot/v1/market/trades'),
        'get_v1_market_depth':      ('GET',  False, 10, '/openApi/spot/v1/market/depth'),       # NAMING CONVENTION DIFF
        'get_market_kline':         ('GET',  False, 10, '/openApi/spot/v2/market/kline'),
        'get_ticker_24hr':          ('GET',  False, 10, '/openApi/spot/v1/ticker/24hr'),
        'get_v2_market_depth':      ('GET',  False, 10, '/openApi/spot/v2/market/depth'),       # NAMING CONVENTION DIFF
        'get_ticker_price':         ('GET',  False, 10, '/openApi/spot/v1/ticker/price'),
        'get_ticker_bookTicker':    ('GET',  False, 10, '/openApi/spot/v1/ticker/bookTicker'),
        'get_v1_kline':             ('GET',  False, 10, '/openApi/market/his/v1/kline'),
        'get_v1_trade':             ('GET',  False, 10, '/openApi/market/his/v1/trade'),
        # wallet - private
        'get_deposit_hisrec':       ('GET',  True,  10, '/openApi/api/v3/capital/deposit/hisrec'),
        'get_withdraw_history':     ('GET',  True,  10, '/openApi/api/v3/capital/withdraw/history'),
        'get_config_getall':        ('GET',  True,  2,  '/openApi/wallets/v1/capital/config/getall'),
        'post_withdraw_apply':      ('POST', True,  2,  '/openApi/wallets/v1/capital/withdraw/apply'),
        'get_deposit_address':      ('GET',  True,  2,  '/openApi/wallets/v1/capital/deposit/address'),
        'get_deposit_riskRecords':  ('GET',  True,  2,  '/openApi/wallets/v1/capital/deposit/riskRecords'),
        # account - private
        'get_account_balance':      ('GET',  True,  5,  '/openApi/spot/v1/account/balance'),
        'post_asset_transfer':      ('POST', True,  2,  '/openApi/api/v3/post/asset/transfer'),
        'get_asset_transfer':       ('GET',  True,  10, '/openApi/api/v3/asset/transfer'),
        'post_innerTransfer_apply': ('POST', True,  2,  '/openApi/wallets/v1/capital/innerTransfer/apply'),
        'get_innerTransfer_records':('GET',  True,  10, '/openApi/wallets/v1/capital/innerTransfer/records'),
        # trade - private
        'post_trade_order':         ('POST', True,  5,  '/openApi/spot/v1/trade/order'),
        'post_trade_cancel':        ('POST', True,  5,  '/openApi/spot/v1/trade/cancel'),
        'post_trade_cancelOrders':  ('POST', True,  2,  '/openApi/spot/v1/trade/cancelOrders'),
        'post_trade_cancelOpenOrders':  ('POST', True,  2,  '/openApi/spot/v1/trade/cancelOpenOrders'),
        'post_order_cancelReplace': ('POST', True,  2,  '/openApi/spot/v1/trade/order/cancelReplace'),
        'get_trade_query':          ('GET',  True,  10, '/openApi/spot/v1/trade/query'),
        'get_trade_openOrders':     ('GET',  True,  10, '/openApi/spot/v1/trade/openOrders'),
        'get_trade_historyOrders':  ('GET',  True,  10, '/openApi/spot/v1/trade/historyOrders'),
        'get_trade_myTrade':        ('GET',  True,  5,  '/openApi/spot/v1/trade/myTrades'),
        'post_trade_batchOrders':   ('POST', True,  2,  '/openApi/spot/v1/trade/batchOrders'),
        'get_user_commissionRate':  ('GET',  True,  2,  '/openApi/spot/v1/user/commissionRate'),
        'post_trade_cancelAllAfter':('POST', True,  2,  '/openApi/spot/v1/trade/cancelAllAfter')
    }

    # Refer: https://bingx-api.github.io/docs/#/en-us/standard/introduce
    standard_futures = {
        # account - private
        'get_v1_allPosition':       ('GET',  True,  5,  '/openApi/contract/v1/allPosition'),
    }

    # common endpoints accessible from all endpoint types
    common = {
        # public
        'get_server_time':          ('GET',  False, '/openApi/swap/v2/server/time')
    }

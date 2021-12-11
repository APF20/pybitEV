"""
To see which endpoints are available, you can read the API docs at
https://bybit-exchange.github.io/docs/inverse/#t-introduction

Some methods will have required parameters, while others may be optional.
The arguments in pybit methods match those provided in the Bybit API
documentation.

The following functions are available:

exit()
set_contract_type()

Public Methods:
------------------------
orderbook()
query_kline()
latest_information_for_symbol()
public_trading_records()
query_symbol()
liquidated_orders()
query_mark_price_kline()
query_index_price_kline()
query_premium_index_kline()
open_interest()
latest_big_deal()
long_short_ratio()
get_the_last_funding_rate()

Private Methods:
(requires authentication)
------------------------
place_active_order()
get_active_order()
cancel_active_order()
cancel_all_active_orders()
replace_active_order()
query_active_order()

place_conditional_order()
get_conditional_order()
cancel_conditional_order()
cancel_all_conditional_orders()
replace_conditional_order()
query_conditional_order()

user_leverage()
change_user_leverage()
cross_isolated_margin_switch()
position_mode_switch()
full_partial_position_tp_sl_switch()

my_position()
change_margin()
set_trading_stop()

get_risk_limit()
set_risk_limit()

my_last_funding_fee()
predicted_funding_rate()

api_key_info()

get_wallet_balance()
wallet_fund_records()
withdraw_records()
user_trade_records()

server_time()
announcement()

Spot Methods:
(many of the above methods can also be used with the spot market,
provided the argument contract_type='spot' is passed,
or set_contract_type('spot') method is called.)
------------------------
fast_cancel_active_order()
batch_cancel_active_order()
batch_fast_cancel_active_order()
batch_cancel_active_order_by_ids()

Asset Transfer Methods:
------------------------
create_internal_transfer()
create_subaccount_transfer()
query_transfer_list()
query_subaccount_transfer_list()
query_subaccount_list()

Custom Methods:
(requires authentication)
------------------------
place_active_order_bulk()
cancel_active_order_bulk()
place_conditional_order_bulk()
cancel_conditional_order_bulk()
close_position()

"""

# Import pybit and asyncio, define a coroutine and HTTP object.
from pybit import HTTP
import asyncio

"""
You can create an authenticated or unauthenticated HTTP session. 
You can skip authentication by not passing any value for api_key
and api_secret.

HTTP class supports both context manager protocol (self closing)
and direct instantiation (manual close required).
"""

# Context manager protocol example

# Lets get market information about EOSUSD, using context manager
# protocol. Note that 'symbol' is a required parameter as per 
# the Bybit API documentation. This is a public endpoint so
# api_key and api_secret can optionally be omitted.

async def main():
    async with HTTP(
        endpoint='https://api.bybit.com',
        api_key='...',
        api_secret='...',
        contract_type='linear'
    ) as session:
        await session.latest_information_for_symbol(symbol='EOSUSD')

asyncio.run(main())

# Direct instantiation example

# Lets get our wallet balance using direct instantiation with 
# manual session closure. This is a private endpoint so api_key
# and api_secret are required.

async def main():
    try:
        session = HTTP(
            endpoint='https://api.bybit.com',
            api_key='...',
            api_secret='...',
            contract_type='linear'
        )
        await session.get_wallet_balance(coin='BTC')
    finally:
        await session.exit()
        
asyncio.run(main())

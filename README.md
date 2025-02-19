# pybitEV
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-3-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

[![Build Status](https://img.shields.io/pypi/pyversions/pybit)](https://www.python.org/downloads/)
[![Build Status](https://img.shields.io/pypi/v/pybit)](https://pypi.org/project/pybit/)
[![Build Status](https://travis-ci.org/verata-veritatis/pybit.svg?branch=master)](https://travis-ci.org/verata-veritatis/pybit)
![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)

Python3 API connector for Bybit's HTTP and Websockets APIs.

## Table of Contents

- [About](#about)
- [Development](#development)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
  * [Market Data Endpoints](#market-data-endpoints)
    + [Advanced Data](#advanced-data)
  * [Account Data Endpoints](#account-data-endpoints)
    + [Active Orders](#active-orders)
    + [Conditional Orders](#conditional-orders)
    + [Position](#position)
    + [Risk Limit](#risk-limit)
    + [Funding](#funding)
    + [API Key Info](#api-key-info)
    + [LCP Info](#lcp-info)
  * [Wallet Data Endpoints](#wallet-data-endpoints)
  * [API Data Endpoints](#api-data-endpoints)
  * [Account Asset Endpoints](#account-asset-endpoints)
  * [WebSocket](#websocket)
    * [Futures](#futures)
      + [Public Topics](#public-topics)
      + [Private Topics](#private-topics)
    + [Spot](#spot)
      + [Public Topics V1](#public-topics-v1)
      + [Public Topics V2](#public-topics-v2)
      + [Private Topics](#private-topics-spot)
- [Contact](#contact)
- [Contributors](#contributors)
- [Donations](#donations)

## About
`PybitEV` is a hard fork of the original Pybit project, upgraded with asyncronous support using the built in asyncio library and the aiohttp library.

Put simply, `pybitEV` (Python + Bybit) is a lightweight one-stop-shop module for the Bybit REST HTTP and WebSocket APIs. I was personally never a fan of auto-generated connectors that used a mosh-pit of various modules you didn't want (sorry, `bravado`) and wanted to build my own Python3-dedicated connector with very little external resources. The goal of the connector is to provide traders and developers with an easy-to-use high-performing module that has an active issue and discussion board leading to consistent improvements.

## Development
After considerable contributions to the original pybit `community` project, I decided to create the `pybitEV` hard fork of the original repository (credit to verata-veritatis for the early iterations) and maintain this fork as a public, true `community` project.

As a user of the module myself, `pybitEV` is being actively developed, especially since Bybit is making changes and improvements to their API on a daily basis (we're still missing some key functions such as bulk order submission or withdrawals). `pybitEV` uses aiohttp for its methods, alongside other built-in modules, such as asyncio, for high performance asyncronous operations.

Feel free to fork this repository, issue reports for any bugs and add pull requests for any improvements.

## Installation
`pybitEV` requires Python 3.7 or higher. The module can be installed manually. Pip installation support will be considered.

## Basic Usage

** Check examples files - below section will be updated shortly for asyncio/aiohttp usage **

You can retrieve the HTTP and WebSocket classes like so:
```python
from pybit import HTTP, WebSocket
```
Create an HTTP session and connect via WebSocket:
```python
session = HTTP(
    endpoint='https://api.bybit.com', 
    api_key='...',
    api_secret='...'
)
ws = WebSocket(
    endpoint='wss://stream.bybit.com/realtime', 
    subscriptions=['order', 'position'], 
    api_key='...',
    api_secret='...'
)
```
Information can be sent to, or retrieved from, the Bybit APIs:
```python
# Get orderbook.
session.orderbook(symbol='BTCUSD')

# Create five long orders.
orders = [{
    'symbol': 'BTCUSD', 
    'order_type': 'Limit', 
    'side': 'Buy', 
    'qty': 100, 
    'price': i,
    'time_in_force': 'GoodTillCancel'
} for i in [5000, 5500, 6000, 6500, 7000]]

# Submit the orders in bulk.
session.place_active_order_bulk(orders)

# Check on your order and position through WebSocket.
ws.fetch('order')
ws.fetch('position')
```
Check out the example python files or the list of endpoints below for more information on available
endpoints and methods. More documentation on the `HTTP` and `WebSocket` methods is available in 
the examples directory.

### Market Data Endpoints

| Endpoint                          | Method |
| -------------                     | ------------- |
| Orderbook                         | `orderbook()`  |
| Query Kline                       | `query_kline()` |
| Latest Information for Symbol     | `latest_information_for_symbol()` |
| Public Trading Records            | `public_trading_records()` |
| Query Symbol                      | `query_symbol()` |
| Liquidated Orders                 | `liquidated_orders()` |
| Query Mark Price Kline            | `query_mark_price_kline()` |
| Open Interest                     | `open_interest()` |

#### Advanced Data

| Endpoint              | Method |
| -------------         | ------------- |
| Query Kline           | `query_kline()` |
| Latest Big Deal       | `latest_big_deal()` |
| Long Short Ratio      | `long_short_ratio()` |

### Account Data Endpoints

#### Active Orders

| Endpoint                                | Method                               |
| --------------------------------------- | ------------------------------------ |
| Place Active Order                      | `place_active_order()`               |
| Get Active Order                        | `get_active_order()`                 |
| Cancel Active Order                     | `cancel_active_order()`              |
| Cancel All Active Orders                | `cancel_all_active_orders()`         |
| Replace Active Order                    | `replace_active_order()`             |
| Query Active Order                      | `query_active_order()`               |
| Fast Cancel Active Order (Spot)         | `fast_cancel_active_order()`         |
| Batch Cancel Active Order (Spot)        | `batch_cancel_active_order()`        |
| Batch Fast Cancel Active Order (Spot)   | `batch_fast_cancel_active_order()`   |
| Batch Cancel Active Order By IDs (Spot) | `batch_cancel_active_order_by_ids()` |

#### Conditional Orders

| Endpoint                          | Method |
| -------------                     | ------------- |
| Place Conditional Order           | `place_conditional_order()`  |
| Get Conditional Order             | `get_conditional_order()`  |
| Cancel Conditional Order          | `cancel_conditional_order()`  |
| Cancel All Conditional Orders     | `cancel_all_conditional_orders()`  |
| Replace Conditional Order         | `replace_conditional_order()`  |
| Query Conditional Order           | `query_conditional_order()` |

#### Position

| Endpoint                                              | Method |
| -------------                                         | ------------- |
| My Position                                           | `my_position()`  |
| Set Auto Add Margin (Linear)                          | `set_auto_add_margin()`  |
| Cross/Isolated Margin Switch (Linear)                 | `cross_isolated_margin_switch()`  |
| Full/Partial Position SL/TP Switch                    | `full_partial_position_tp_sl_switch` |
| Add/Reduce Margin (Linear)                            | `add_reduce_margin()` |
| Set Trading-Stop                                      | `set_trading_stop()`  |
| Set Leverage                                          | `set_leverage()`  |
| User Leverage (deprecated)                            | `user_leverage()` |
| User Trade Records                                    | `user_trade_records()`  |
| Closed Profit and Loss                                | `closed_profit_and_loss()` |

#### Risk Limit

| Endpoint                      | Method |
| -------------                 | ------------- |
| Get Risk Limit                | `my_position()`  |
| Set Risk Limit (Inverse)      | `set_auto_add_margin()`  |

#### Funding

| Endpoint                                      | Method |
| -------------                                 | ------------- |
| Get the Last Funding Rate                     | `get_the_last_funding_rate()`  |
| My Last Funding Fee                           | `my_last_funding_fee()`  |
| Predicted Funding Rate and My Funding Fee     | `predicted_funding_rate()` |

#### API Key Info

| Endpoint          | Method |
| -------------     | ------------- |
| API Key Info      | `api_key_info()`  |

#### LCP Info

| Endpoint          | Method |
| -------------     | ------------- |
| LCP Info          | `lcp_info()`  |

### Wallet Data Endpoints

| Endpoint                  | Method |
| -------------             | ------------- |
| Get Wallet Balance        | `get_wallet_balance()`  |
| Wallet Fund Records       | `wallet_fund_records()`  |
| Withdraw Records          | `withdraw_records()`  |
| Asset Exchange Records    | `asset_exchange_records()` |

### API Data Endpoints

| Endpoint           | Method |
| -------------      | ------------- |
| Server Time        | `server_time()`  |
| Announcement       | `announcement()`  |

### Account Asset Endpoints

| Endpoint                       | Method                             |
| ------------------------------ | ---------------------------------- |
| Create Internal Transfer       | `create_internal_transfer()`       |
| Create Subaccount Transfer     | `create_subaccount_transfer()`     |
| Query Transfer List            | `query_transfer_list()`            |
| Query Subaccount Transfer List | `query_subaccount_transfer_list()` |
| Query Subaccount List          | `query_subaccount_list()`          |

### pybit Custom Endpoints

| Endpoint                          | Method |
| -------------                     | ------------- |
| Place Active Order (Bulk)         | `place_active_order_bulk()`  |
| Cancel Active Order (Bulk)        | `cancel_active_order_bulk()`  |
| Place Conditional Order (Bulk)    | `place_conditional_order_bulk()`  |
| Cancel Conditional Order (Bulk)   | `cancel_conditional_order_bulk()`  |
| Close Position                    | `close_position()` |

### WebSocket

To see comprehensive examples of how to subscribe to the futures and spot websockets, check the examples files.

#### Futures
##### Public Topics

| Topic Name            | Topic String |
| -------------         | ------------- |
| orderBookL2_25        | `'orderBookL2_25'`  |
| orderBookL2_200       | `'orderBookL2_200'`  |
| trade                 | `'trade'`  |
| insurance             | `'insurance'`  |
| instrument_info       | `'instrument_info'`  |
| klineV2               | `'klineV2'`  |

##### Private Topics

| Topic Name            | Topic String |
| -------------         | ------------- |
| position              | `'position'`  |
| execution             | `'execution'`  |
| order                 | `'order'`  |
| stop_order            | `'stop_order'`  |

#### Spot
Topic names for spot are listed here, but not the topic strings. This is because the spot websocket uses a JSON for topics and their filters/parameters, rather than a single string for both. As a result, a topic string cannot be used to `ws.fetch()` data. You can find a complete list of sample JSONs for subscribing to each spot topic in the [official API documentation](https://bybit-exchange.github.io/docs/spot/#t-publictopics).

To see how to use these JSONs with pybit, please check the example files.

##### Public Topics V1
| Topic Name  |
| ----------- |
| trade       |
| realtimes   |
| kline       |
| depth       |
| mergedDepth |
| diffDepth   |

##### Public Topics V2
| Topic Name |
| ---------- |
| depth      |
| kline      |
| trade      |
| bookTicker |
| realtimes  |

##### Private Topics (Spot)
| Topic Name          |
| ------------------- |
| outboundAccountInfo |
| executionReport     |
| ticketInfo          |

## Contact
I'm pretty active on the [BybitAPI Telegram](https://t.me/BybitAPI) group chat.

## Contributors

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
      <td align="center"><a href="https://github.com/APF20"><img src="https://avatars0.githubusercontent.com/u/74583612?v=4" width="100px;" alt=""/><br /><sub><b>APF20</b></sub></a><br /><a href="https://github.com/verata-veritatis/pybit/commits?author=APF20" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/verata-veritatis"><img src="https://avatars0.githubusercontent.com/u/9677388?v=4" width="100px;" alt=""/><br /><sub><b>verata-veritatis</b></sub></a><br /><a href="https://github.com/verata-veritatis/pybit/commits?author=verata-veritatis" title="Code">💻</a> <a href="https://github.com/verata-veritatis/pybit/commits?author=verata-veritatis" title="Documentation">📖</a></td>
      <td align="center"><a href="https://github.com/cameronhh"><img src="https://avatars0.githubusercontent.com/u/30434979?v=4" width="100px;" alt=""/><br /><sub><b>Cameron Harder-Hutton</b></sub></a><br /><a href="https://github.com/verata-veritatis/pybit/commits?author=cameronhh" title="Code">💻</a></td>
     <td align="center"><a href="https://github.com/tconley"><img src="https://avatars1.githubusercontent.com/u/1893207?v=4" width="100px;" alt=""/><br /><sub><b>Todd Conley</b></sub></a><br /><a href="https://github.com/tconley/pybit/commits?author=tconley" title="Ideas">🤔</a></td>
  </tr>
</table>

<!-- markdownlint-enable -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

## Donations

I work on `pybit` in my spare time, along with other contributors. If you like the project and want to donate, you can do so to the following addresses:

```
XTZ:
BTC:
ETH:
```

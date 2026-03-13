# pybitEV
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-3-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

[![Build Status](https://img.shields.io/pypi/pyversions/pybit)](https://www.python.org/downloads/)
[![Build Status](https://img.shields.io/pypi/v/pybit)](https://pypi.org/project/pybitEV/)
[![Build Status](https://travis-ci.org/apf20/pybitev.svg?branch=master)](https://travis-ci.org/apf20/pybitev)
![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)

Python3 API connector for Bybit's HTTP and Websockets APIs.

## Table of Contents

- [About](#about)
- [Development](#development)
- [Installation](#installation)
- [Usage](#usage)
- [Contact](#contact)
- [Contributors](#contributors)
- [Donations](#donations)

## About
Put simply, `PybitEV` is a hard fork of the original Pybit project, upgraded with fast asyncronous support, using the built in `asyncio` library and the `aiohttp` library. `pybitEV` (Python + Bybit) is a lightweight one-stop-shop module for the Bybit REST HTTP and WebSocket APIs.

I was personally never a fan of auto-generated connectors that used a mosh-pit of 
various modules you didn't want (sorry, `bravado`) and wanted to build my own 
Python3-dedicated connector with very little external resources. The goal of the 
connector is to provide traders and developers with an easy-to-use high-performing 
module that has an active issue and discussion board leading to consistent improvements.

## Development
After considerable contributions to the original pybit `community` project, I decided to
create the `pybitEV` hard fork of the original repository (credit to verata-veritatis for
the early iterations) and maintain this fork as a public, true `community` project.

`pybitEV` was being actively developed, especially since Bybit was making changes and
improvements to their API on a daily basis (we're still missing some key functions such
as bulk order submission or withdrawals). It is compatible up to V2 of the Bybit APIs.
`pybitEV` uses aiohttp for its methods, alongside other built-in modules, such as asyncio,
for high performance asyncronous operations.

Feel free to fork this repository, issue reports for any bugs and add pull requests for any improvements.

## Installation
`pybitEV` requires Python 3.8 or higher. The module can be installed manually. Pip 
installation support will be considered.

## Usage
You can retrieve the HTTP and WebSocket classes like so:
```python
import asyncio
from pybit import Exchange
```
Create an HTTP session and connect via WebSocket using context manager protocol:
```python
async def main():
    async with Exchange() as session:
        rest = session.rest(
            endpoint='https://api.bybit.com',
            api_key='...',
            api_secret='...',
            contract_type='linear'
        )
        ws = session.websocket(
            endpoint='wss://stream.bybit.com/realtime',
            subscriptions=['instrument_info.100ms.ETHUSD']
        )
asyncio.run(main())
```
Information can be sent to, or retrieved from, the Bybit APIs:
```python
async def main():
    async with Exchange() as session:
        rest = session.rest(...)

        # Get orderbook.
        print(await rest.orderbook(symbol='EOSUSD'))

        # Create five long orders.
        orders = [{
            'symbol': 'BTCUSD', 
            'order_type': 'Limit', 
            'side': 'Buy', 
            'qty': 100, 
            'price': i,
            'time_in_force': 'GoodTillCancel'
        } for i in [5000, 5500, 6000, 6500, 7000]]

        # Submit the orders in bulk, asyncronously.
        await rest.place_active_order_bulk(orders, max_in_parallel=10) 

asyncio.run(main())
```
Check out the example python files for more information on available endpoints and methods. More documentation and examples on the `HTTP` and `WebSocket` methods is available in the examples directory.

## Contact
I'm pretty active on the [BybitAPI Telegram](https://t.me/BybitAPI) group chat.

## Contributors

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
      <td align="center"><a href="https://github.com/APF20"><img src="https://avatars0.githubusercontent.com/u/74583612?v=4" width="100px;" alt=""/><br /><sub><b>APF20</b></sub></a><br /><a href="https://github.com/APF20/pybitEV/commits?author=APF20" title="Code">💻</a>  <a href="https://github.com/APF20/pybitEV/commits?author=APF20" title="Documentation">📖</a></td>
      <td align="center"><a href="https://github.com/verata-veritatis"><img src="https://avatars0.githubusercontent.com/u/9677388?v=4" width="100px;" alt=""/><br /><sub><b>verata-veritatis</b></sub></a><br /><a href="https://github.com/verata-veritatis/pybit/commits?author=verata-veritatis" title="Code">💻</a></td>
  </tr>
</table>

<!-- markdownlint-enable -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

## Donations

I work on `pybit` in my spare time. If you like the project and want to donate, you can do so to the following addresses:

```
SOL: HoUMsBKUESB9fsVTNtT4jYGnAzTAH9LNpZHjXvPiZ5Tb
BTC: bc1q4y230tg3rrhty9zxwpm63g5sgaqxw83xuwahjk
ETH: 0x06fd9aad799c5f094ce8c941fae9b81967cd8323
```

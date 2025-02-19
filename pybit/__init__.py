# -*- coding: utf-8 -*-

"""
pybitEV
------------------------

pybitEV is a lightweight, high-performance and asyncronous API
connector for the RESTful and WebSocket APIs of the Bybit exchange.

Documentation can be found at
https://github.com/APF20/pybit

:copyright: (c) 2020 APF20
:license: MIT License

"""

import time
import hmac
import asyncio
import aiohttp
import json

from .exceptions import FailedRequestError, InvalidRequestError, WebSocketException
from . import log

#
# Helpers
#
LOGGER = log.setup_custom_logger('root', streamLevel='INFO')

VERSION = '3.7.0'


class Exchange:
    """
    Exchange Interface for pybitEV REST and WebSocket API
    """

    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.logger = LOGGER

    async def __aenter__(self):
        return self

    async def __aexit__(self, *err):
        await self.exit()

    async def exit(self):
        """Closes the aiohttp session."""
        await self.session.close()
        self.logger.info('Exchange session closed.')

    def rest(self, **kwargs):
        """
        Create REST HTTP Object.

        :param kwargs: See HTTP Class.
        :returns: REST HTTP Object.
        """
        return HTTP(self.session, **kwargs)

    def websocket(self, endpoint, **kwargs):
        """
        Create WebSocket Object.

        :param kwargs: See WebSocket Class.
        :returns: REST WebSocket Object.
        """
        return WebSocket(self.session, endpoint, **kwargs)

    @property
    def clientSession(self):
        return self.session


class HTTP:
    """
    Connector for Bybit's HTTP API.

    :param session: Required parameter. An aiohttp ClientSession constructed
        session instance.
    :type session: obj

    :param endpoint: The base endpoint URL of the REST HTTP API, e.g.
        'https://api-testnet.bybit.com'.
    :type endpoint: str

    :param api_key: Your API key. Required for authenticated endpoints. Defaults
        to None.
    :type api_key: str

    :param api_secret: Your API secret key. Required for authenticated
        endpoints. Defaults to None.
    :type api_secret: str

    :param logging_level: The logging level of the built-in logger. Defaults to
        logging.INFO. Options are CRITICAL (50), ERROR (40), WARNING (30),
        INFO (20), DEBUG (10), or NOTSET (0).
    :type logging_level: Union[int, logging.level]

    :param log_requests: Whether or not pybit should log each HTTP request.
    :type log_requests: bool

    :param request_timeout: The timeout of each API request in seconds. Defaults
        to 10 seconds.
    :type request_timeout: int

    :param recv_window: How long an HTTP request is valid in ms. Default is
        5000.
    :type recv_window: int

    :param force_retry: Whether or not pybit should retry a timed-out request.
    :type force_retry: bool

    :param retry_codes: A list of non-fatal status codes to retry on.
    :type retry_codes: set

    :param ignore_codes: A list of non-fatal status codes to ignore.
    :type ignore_codes: set

    :param max_retries: The number of times to re-attempt a request.
    :type max_retries: int

    :param retry_delay: Seconds between retries for returned error or timed-out
        requests. Default is 3 seconds.
    :type retry_delay: int

    :param referral_id: An optional referer ID can be added to each request for
        identification.
    :type referral_id: str

    :param contract_type: The contract type endpoints to use for requests. e.g.
        'linear', 'inverse', 'futures', 'spot'. Can be dynamically changed by
        using set_contract_type().
    :type contract_type: str

    :returns: pybit.HTTP session.

    """

    def __init__(self, session, endpoint=None, api_key=None, api_secret=None,
                 logging_level='INFO', log_requests=False, request_timeout=10,
                 recv_window=5000, force_retry=False, retry_codes=None,
                 ignore_codes=None, max_retries=3, retry_delay=3,
                 referral_id=None, contract_type=None):

        """Initializes the HTTP class."""

        # Set the base endpoint url.
        self.url = 'https://api.bybit.com' if not endpoint else endpoint

        # Setup logger.
        self.logger = LOGGER
        self.logger.info('Initializing HTTP session.')
        self.log_requests = log_requests

        # Set API keys.
        self.api_key = api_key
        self.api_secret = api_secret

        # Set timeout to ClientTimeout sentinel.
        self.timeout = aiohttp.ClientTimeout(sock_read=request_timeout)
        self.recv_window = recv_window
        self.force_retry = force_retry
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Set whitelist of non-fatal Bybit status codes to retry on.
        self.retry_codes = {
            10002,      # request expired, check your timestamp and recv_window
            10006,      # too many requests
            10016,      # connect to server fail (general)
            30034,      # no order found (non-linear)
            30035,      # too fast to cancel (non-linear)
            130035,     # Too freq to cancel, Try it later (linear)
            130150      # Please try again later (linear)
        } if not retry_codes else retry_codes

        # Set whitelist of non-fatal Bybit status codes to ignore.
        self.ignore_codes = {} if not ignore_codes else ignore_codes

        # Set aiohttp client session.
        self.session = session

        # Set default aiohttp headers.
        self.headers = {
            'User-Agent': 'pybit-' + VERSION,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        # Add referral ID to header.
        if referral_id:
            self.headers['Referer'] = self.referral_id

        # Set contract type
        self.set_contract_type(contract_type)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *err):
        await self.exit()

    async def exit(self):
        """Closes the aiohttp session."""
        await self.session.close()
        self.logger.info('HTTP session closed.')

    async def _sem_gather(self, n: int, *aws):
        """Semaphore async gather with concurrent rate limit"""

        sem = asyncio.BoundedSemaphore(n)

        async def sem_task(task):
            async with sem:
                return await task

        return await asyncio.gather(*(sem_task(task) for task in aws))

    def set_contract_type(self, type: str):
        """
        Set contract_type var and endpoints dict based on contract type.

        :param type: str Contract type e.g. linear, inverse, futures, spot
        """

        self.contract_type = type

        if type:
            self.logger.info(f'Using {type} contract type endpoints.')

        if type == 'linear':
            self.endpoints = {
                'query_kline':                  '/public/linear/kline',
                'public_trading_records':       '/public/linear/recent-trading-records',
                'query_mark_price_kline':       '/public/linear/mark-price-kline',
                'query_index_price_kline':      '/public/linear/index-price-kline',
                'query_premium_index_kline':    '/public/linear/premium-index-kline',
                'place_active_order':           '/private/linear/order/create',
                'get_active_order':             '/private/linear/order/list',
                'cancel_active_order':          '/private/linear/order/cancel',
                'cancel_all_active_orders':     '/private/linear/order/cancel-all',
                'replace_active_order':         '/private/linear/order/replace',
                'query_active_order':           '/private/linear/order/search',
                'place_conditional_order':      '/private/linear/stop-order/create',
                'get_conditional_order':        '/private/linear/stop-order/list',
                'cancel_conditional_order':     '/private/linear/stop-order/cancel',
                'cancel_all_conditional_orders':'/private/linear/stop-order/cancel-all',
                'replace_conditional_order':    '/private/linear/stop-order/replace',
                'query_conditional_order':      '/private/linear/stop-order/search',
                'my_position':                  '/private/linear/position/list',
                'set_auto_add_margin':          '/private/linear/position/set-auto-add-margin',
                'set_leverage':                 '/private/linear/position/set-leverage',
                'cross_isolated_margin_switch': '/private/linear/position/switch-isolated',
                'position_mode_switch':         '/private/linear/position/switch-mode',
                'full_partial_position_tp_sl_switch':   '/private/linear/tpsl/switch-mode',
                'set_trading_stop':             '/private/linear/position/trading-stop',
                'add_reduce_margin':            '/private/linear/position/add-margin',
                'user_trade_records':           '/private/linear/trade/execution/list',
                'closed_profit_and_loss':       '/private/linear/trade/closed-pnl/list',
                'get_risk_limit':               '/public/linear/risk-limit',
                'set_risk_limit':               '/private/linear/position/set-risk',
                'get_the_last_funding_rate':    '/public/linear/funding/prev-funding-rate',
                'my_last_funding_fee':          '/private/linear/funding/prev-funding',
                'predicted_funding_rate':       '/private/linear/funding/predicted-funding'
            }

        elif type == 'inverse':
            self.endpoints = {
                'query_kline':                  '/v2/public/kline/list',
                'public_trading_records':       '/v2/public/trading-records',
                'query_mark_price_kline':       '/v2/public/mark-price-kline',
                'query_index_price_kline':      '/v2/public/index-price-kline',
                'query_premium_index_kline':    '/v2/public/premium-index-kline',
                'place_active_order':           '/v2/private/order/create',
                'get_active_order':             '/v2/private/order/list',
                'cancel_active_order':          '/v2/private/order/cancel',
                'cancel_all_active_orders':     '/v2/private/order/cancelAll',
                'replace_active_order':         '/v2/private/order/replace',
                'query_active_order':           '/v2/private/order',
                'place_conditional_order':      '/v2/private/stop-order/create',
                'get_conditional_order':        '/v2/private/stop-order/list',
                'cancel_conditional_order':     '/v2/private/stop-order/cancel',
                'cancel_all_conditional_orders':'/v2/private/stop-order/cancelAll',
                'replace_conditional_order':    '/v2/private/stop-order/replace',
                'query_conditional_order':      '/v2/private/stop-order',
                'my_position':                  '/v2/private/position/list',
                'set_leverage':                 '/v2/private/position/leverage/save',
                'cross_isolated_margin_switch': '/v2/private/position/switch-isolated',
                'query_trading_fee_rate':       '/v2/private/position/fee-rate',
                'position_mode_switch':         '/v2/private/position/switch-mode',
                'full_partial_position_tp_sl_switch':   '/v2/private/tpsl/switch-mode',
                'change_margin':                '/v2/private/position/change-position-margin',
                'set_trading_stop':             '/v2/private/position/trading-stop',
                'user_trade_records':           '/v2/private/execution/list',
                'closed_profit_and_loss':       '/v2/private/trade/closed-pnl/list',
                'get_risk_limit':               '/v2/public/risk-limit/list',
                'set_risk_limit':               '/v2/private/position/risk-limit',
                'get_the_last_funding_rate':    '/v2/public/funding/prev-funding-rate',
                'my_last_funding_fee':          '/v2/private/funding/prev-funding',
                'predicted_funding_rate':       '/v2/private/funding/predicted-funding'
            }

        elif type == 'futures':
            self.endpoints = {
                'query_kline':                  '/v2/public/kline/list',
                'public_trading_records':       '/v2/public/trading-records',
                'query_mark_price_kline':       '/v2/public/mark-price-kline',
                'query_index_price_kline':      '/v2/public/index-price-kline',
                'query_premium_index_kline':    '/v2/public/premium-index-kline',
                'place_active_order':           '/futures/private/order/create',
                'get_active_order':             '/futures/private/order/list',
                'cancel_active_order':          '/futures/private/order/cancel',
                'cancel_all_active_orders':     '/futures/private/order/cancelAll',
                'replace_active_order':         '/futures/private/order/replace',
                'query_active_order':           '/futures/private/order',
                'place_conditional_order':      '/futures/private/stop-order/create',
                'get_conditional_order':        '/futures/private/stop-order/list',
                'cancel_conditional_order':     '/futures/private/stop-order/cancel',
                'cancel_all_conditional_orders':'/futures/private/stop-order/cancelAll',
                'replace_conditional_order':    '/futures/private/stop-order/replace',
                'query_conditional_order':      '/futures/private/stop-order',
                'my_position':                  '/futures/private/position/list',
                'set_leverage':                 '/futures/private/position/leverage/save',
                'cross_isolated_margin_switch': '/futures/private/position/switch-mode',
                'position_mode_switch':         '/futures/private/position/switch-mode',
                'full_partial_position_tp_sl_switch':   '/futures/private/tpsl/switch-mode',
                'change_margin':                '/futures/private/position/change-position-margin',
                'set_trading_stop':             '/futures/private/position/trading-stop',
                'user_trade_records':           '/futures/private/execution/list',
                'closed_profit_and_loss':       '/futures/private/trade/closed-pnl/list',
                'get_risk_limit':               '/v2/public/risk-limit/list',
                'set_risk_limit':               '/futures/private/position/risk-limit'
            }

        elif type == 'spot':
            self.endpoints = {
                'orderbook':                    '/spot/quote/v1/depth',
                'merged_orderbook':             '/spot/quote/v1/depth/merged',
                'query_kline':                  '/spot/quote/v1/kline',
                'latest_information_for_symbol':'/spot/quote/v1/ticker/24hr',
                'last_traded_price':            '/spot/quote/v1/ticker/price',
                'best_bid_ask_price':           '/spot/quote/v1/ticker/book_ticker',
                'public_trading_records':       '/spot/quote/v1/trades',
                'query_symbol':                 '/spot/v1/symbols',
                'place_active_order':           '/spot/v1/order',
                'cancel_active_order':          '/spot/v1/order',
                'fast_cancel_active_order':     '/spot/v1/order/fast',
                'batch_cancel_active_order':    '/spot/order/batch-cancel',
                'batch_fast_cancel_active_order':'/spot/order/batch-fast-cancel',
                'batch_cancel_active_order_by_ids':     '/spot/order/batch-cancel-by-ids',
                'get_active_order':             '/spot/v1/order',
                'open_orders':                  '/spot/v1/open-orders',
                'order_history':                '/spot/v1/history-orders',
                'user_trade_records':           '/spot/v1/myTrades',
                'get_wallet_balance':           '/spot/v1/account',
                'server_time':                  '/spot/v1/time'
            }

        elif not type:
            self.endpoints = {}
            self.logger.warning(
                'Contract type is not set. Only account asset endpoints are available. '
                'Use contract_type init param or set_contract_type() to set/change.'
            )

        # add shared endpoints for linear, inverse and futures
        if type in {'linear', 'inverse', 'futures'}:
            self.endpoints.update({
                'orderbook':                    '/v2/public/orderBook/L2',
                'latest_information_for_symbol':'/v2/public/tickers',
                'query_symbol':                 '/v2/public/symbols',
                'open_interest':                '/v2/public/open-interest',
                'latest_big_deal':              '/v2/public/big-deal',
                'change_user_leverage':         '/user/leverage/save',
                'long_short_ratio':             '/v2/public/account-ratio',
                'api_key_info':                 '/v2/private/account/api-key',
                'lcp_info':                     '/v2/private/account/lcp',
                'get_wallet_balance':           '/v2/private/wallet/balance',
                'wallet_fund_records':          '/v2/private/wallet/fund/records',
                'withdraw_records':             '/v2/private/wallet/withdraw/list',
                'asset_exchange_records':       '/v2/private/exchange-order/list',
                'server_time':                  '/v2/public/time',
                'announcement':                 '/v2/public/announcement'
            })

        # add common endpoints for account asset
        self.endpoints.update({
            'create_internal_transfer':         '/asset/v1/private/transfer',
            'create_subaccount_transfer':       '/asset/v1/private/sub-member/transfer',
            'query_transfer_list':              '/asset/v1/private/transfer/list',
            'query_subaccount_list':            '/asset/v1/private/sub-member/member-ids',
            'query_subaccount_transfer_list':   '/asset/v1/private/sub-member/transfer/list'
        })

    async def orderbook(self, **kwargs):
        """
        Get the orderbook.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-orderbook.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['orderbook'],
            query=kwargs
        )

    async def merged_orderbook(self, **kwargs):
        """
        Get the merged orderbook.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/spot/#t-mergedorderbook.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['merged_orderbook'],
            query=kwargs
        )

    async def query_kline(self, **kwargs):
        """
        Get kline.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-querykline.
        :returns: Request results as dictionary.
        """

        # Replace query param 'from_time' since 'from' keyword is reserved.
        # Temporary workaround until Bybit updates official request params
        if 'from_time' in kwargs:
            kwargs['from'] = kwargs.pop('from_time')

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['query_kline'],
            query=kwargs
        )

    async def latest_information_for_symbol(self, **kwargs):
        """
        Get the latest information for symbol.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-latestsymbolinfo.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['latest_information_for_symbol'],
            query=kwargs
        )

    async def last_traded_price(self, **kwargs):
        """
        Get the last traded price for symbol.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/spot/#t-lasttradedprice.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['last_traded_price'],
            query=kwargs
        )

    async def best_bid_ask_price(self, **kwargs):
        """
        Get the best bid and ask prices and quantities for symbol.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/spot/#t-bestbidask.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['best_bid_ask_price'],
            query=kwargs
        )

    async def public_trading_records(self, **kwargs):
        """
        Get recent trades. You can find a complete history of trades on Bybit
        at https://public.bybit.com/.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-publictradingrecords.
        :returns: Request results as dictionary.
        """

        # Replace query param 'from_id' since 'from' keyword is reserved.
        # Temporary workaround until Bybit updates official request params
        if 'from_id' in kwargs:
            kwargs['from'] = kwargs.pop('from_id')

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['public_trading_records'],
            query=kwargs
        )

    async def query_symbol(self):
        """
        Get symbol info.

        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['query_symbol']
        )

    def liquidated_orders(self, **kwargs):
        """
        ABANDONED! Please use liquidation websocket instead. Retrieve the
        liquidated orders. The query range is the last seven days of data.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-query_liqrecords.
        :returns: Request results as dictionary.
        """

        raise Exception('This endpoint has been removed. Use liquidation websocket')

        # Replace query param 'from_id' since 'from' keyword is reserved.
        # Temporary workaround until Bybit updates official request params
        if 'from_id' in kwargs:
            kwargs['from'] = kwargs.pop('from_id')

        return self._submit_request(
            method='GET',
            path=self.endpoint + '/v2/public/liq-records',
            query=kwargs
        )

    async def query_mark_price_kline(self, **kwargs):
        """
        Query mark price kline (like query_kline but for mark price).

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-markpricekline.
        :returns: Request results as dictionary.
        """

        # Replace query param 'from_time' since 'from' keyword is reserved.
        # Temporary workaround until Bybit updates official request params
        if 'from_time' in kwargs:
            kwargs['from'] = kwargs.pop('from_time')

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['query_mark_price_kline'],
            query=kwargs
        )

    async def query_index_price_kline(self, **kwargs):
        """
        Query index price kline. Index price kline. Tracks BTC spot prices,
        with a frequency of every second.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-queryindexpricekline.
        :returns: Request results as dictionary.
        """

        # Replace query param 'from_time' since 'from' keyword is reserved.
        # Temporary workaround until Bybit updates official request params
        if 'from_time' in kwargs:
            kwargs['from'] = kwargs.pop('from_time')
 
        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['query_index_price_kline'],
            query=kwargs
        )

    async def query_premium_index_kline(self, **kwargs):
        """
        Query premium index kline. Tracks the premium / discount of BTC
        perpetual contracts relative to the mark price per minute

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-querypremiumindexkline.
        :returns: Request results as dictionary.
        """

        # Replace query param 'from_time' since 'from' keyword is reserved.
        # Temporary workaround until Bybit updates official request params
        if 'from_time' in kwargs:
            kwargs['from'] = kwargs.pop('from_time')

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['query_premium_index_kline'],
            query=kwargs
        )

    async def open_interest(self, **kwargs):
        """
        Gets the total amount of unsettled contracts. In other words, the total
        number of contracts held in open positions.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-marketopeninterest.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['open_interest'],
            query=kwargs
        )

    async def latest_big_deal(self, **kwargs):
        """
        Obtain filled orders worth more than 500,000 USD within the last 24h.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-marketbigdeal.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['latest_big_deal'],
            query=kwargs
        )

    async def long_short_ratio(self, **kwargs):
        """
        Gets the Bybit long-short ratio.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-marketaccountratio.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['long_short_ratio'],
            query=kwargs
        )

    async def place_active_order(self, **kwargs):
        """
        Places an active order.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-activeorders.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['place_active_order'],
            query=kwargs,
            auth=True
        )

    async def place_active_order_bulk(self, orders: list, max_in_parallel=10):
        """
        Places multiple active orders in bulk using async concurrency. For more
        information on place_active_order, see
        https://bybit-exchange.github.io/docs/inverse/#t-activeorders.

        :param list orders: A list of orders and their parameters.
        :param max_in_parallel: The number of requests to be sent in parallel.
            Note that you are limited to 50 requests per second.
        :returns: Future request result dictionaries as a list.
        """

        res = await self._sem_gather(
            max_in_parallel,
            *[self.place_active_order(**order) for order in orders]
        )
        return [r for r in res]

    async def get_active_order(self, **kwargs):
        """
        Gets an active order.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-getactive.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['get_active_order'],
            query=kwargs,
            auth=True
        )

    async def cancel_active_order(self, **kwargs):
        """
        Cancels an active order.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-cancelactive.
        :returns: Request results as dictionary.
        """

        method = 'DELETE' if self.contract_type == 'spot' else 'POST'

        return await self._submit_request(
            method=method,
            path=self.url + self.endpoints['cancel_active_order'],
            query=kwargs,
            auth=True
        )

    async def fast_cancel_active_order(self, **kwargs):
        """
        Cancels an active order.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/spot/#t-fastcancelactiveorder.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='DELETE',
            path=self.url + self.endpoints['fast_cancel_active_order'],
            query=kwargs,
            auth=True
        )

    async def cancel_active_order_bulk(self, orders: list, max_in_parallel=10):
        """
        Cancels multiple active orders in bulk using async concurrency. For more
        information on cancel_active_order, see
        https://bybit-exchange.github.io/docs/inverse/#t-activeorders.

        :param list orders: A list of orders and their parameters.
        :param max_in_parallel: The number of requests to be sent in parallel.
            Note that you are limited to 50 requests per second.
        :returns: Future request result dictionaries as a list.
        """

        res = await self._sem_gather(
            max_in_parallel,
            *[self.cancel_active_order(**order) for order in orders]
        )
        return [r for r in res]

    async def cancel_all_active_orders(self, **kwargs):
        """
        Cancel all active orders that are unfilled or partially filled. Fully
        filled orders cannot be cancelled.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-cancelallactive.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['cancel_all_active_orders'],
            query=kwargs,
            auth=True
        )

    async def batch_cancel_active_order(self, **kwargs):
        """
        Cancel all active orders by symbol, side and orderTypes.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/spot/#t-batchcancelactiveorder.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='DELETE',
            path=self.url + self.endpoints['batch_cancel_active_order'],
            query=kwargs,
            auth=True
        )

    async def batch_fast_cancel_active_order(self, **kwargs):
        """
        Fast cancel all active orders by symbol, side and orderTypes.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/spot/#t-batchfastcancelactiveorder.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='DELETE',
            path=self.url + self.endpoints['batch_fast_cancel_active_order'],
            query=kwargs,
            auth=True
        )

    async def batch_cancel_active_order_by_ids(self, **kwargs):
        """
        Cancel active orders by matching orderIds.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/spot/#t-batchcancelactiveorderbyids.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='DELETE',
            path=self.url + self.endpoints['batch_cancel_active_order_by_ids'],
            query=kwargs,
            auth=True
        )

    async def replace_active_order(self, **kwargs):
        """
        Replace order can modify/amend your active orders.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-replaceactive.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['replace_active_order'],
            query=kwargs,
            auth=True
        )

    async def replace_active_order_bulk(self, orders: list, max_in_parallel=10):
        """
        Replaces multiple active orders in bulk using async concurrency. For more
        information on replace_active_order, see
        https://bybit-exchange.github.io/docs/inverse/#t-replaceactive.

        :param list orders: A list of orders and their parameters.
        :param max_in_parallel: The number of requests to be sent in parallel.
            Note that you are limited to 50 requests per second.
        :returns: Future request result dictionaries as a list.
        """

        res = await self._sem_gather(
            max_in_parallel,
            *[self.replace_active_order(**order) for order in orders]
        )
        return [r for r in res]

    async def query_active_order(self, **kwargs):
        """
        Query real-time active order information. For spot contracts
            use get_active_order() or open_orders() as 'orderId' param
            is optionally used as a filter for both functions.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-queryactive.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['query_active_order'],
            query=kwargs,
            auth=True
        )

    async def open_orders(self, **kwargs):
        """
        Get open active order information.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/spot/#t-openorders.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['open_orders'],
            query=kwargs,
            auth=True
        )

    async def order_history(self, **kwargs):
        """
        Get order history information.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/spot/#t-orderhistory.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['order_history'],
            query=kwargs,
            auth=True
        )

    async def place_conditional_order(self, **kwargs):
        """
        Places a conditional order. For more information, see
        https://bybit-exchange.github.io/docs/inverse/#t-placecond.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-placecond.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['place_conditional_order'],
            query=kwargs,
            auth=True
        )

    async def place_conditional_order_bulk(self, orders: list, max_in_parallel=10):
        """
        Places multiple conditional orders in bulk using async concurrency. For
        more information on place_active_order, see
        https://bybit-exchange.github.io/docs/inverse/#t-placecond.

        :param orders: A list of orders and their parameters.
        :param max_in_parallel: The number of requests to be sent in parallel.
            Note that you are limited to 50 requests per second.
        :returns: Future request result dictionaries as a list.
        """

        res = await self._sem_gather(
            max_in_parallel,
            *[self.place_conditional_order(**order) for order in orders]
        )
        return [r for r in res]

    async def get_conditional_order(self, **kwargs):
        """
        Gets a conditional order. For more information, see
        https://bybit-exchange.github.io/docs/inverse/#t-getcond.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-getcond.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['get_conditional_order'],
            query=kwargs,
            auth=True
        )

    async def cancel_conditional_order(self, **kwargs):
        """
        Cancels a conditional order. For more information, see
        https://bybit-exchange.github.io/docs/inverse/#t-cancelcond.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-cancelcond.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['cancel_conditional_order'],
            query=kwargs,
            auth=True
        )

    async def cancel_conditional_order_bulk(self, orders: list, max_in_parallel=10):
        """
        Cancels multiple conditional orders in bulk using async concurrency. For
        more information on cancel_active_order, see
        https://bybit-exchange.github.io/docs/inverse/#t-cancelcond.

        :param list orders: A list of orders and their parameters.
        :param max_in_parallel: The number of requests to be sent in parallel.
            Note that you are limited to 50 requests per second.
        :returns: Future request result dictionaries as a list.
        """

        res = await self._sem_gather(
            max_in_parallel,
            *[self.cancel_conditional_order(**order) for order in orders]
        )
        return [r for r in res]

    async def cancel_all_conditional_orders(self, **kwargs):
        """
        Cancel all conditional orders that are unfilled or partially filled.
        Fully filled orders cannot be cancelled.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-cancelallcond.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['cancel_all_conditional_orders'],
            query=kwargs,
            auth=True
        )

    async def replace_conditional_order(self, **kwargs):
        """
        Replace conditional order can modify/amend your conditional orders.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-replacecond.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['replace_conditional_order'],
            query=kwargs,
            auth=True
        )

    async def replace_conditional_order_bulk(self, orders: list, max_in_parallel=10):
        """
        Replaces multiple conditional orders in bulk using async concurrency. For
        more information on replace_active_order, see
        https://bybit-exchange.github.io/docs/inverse/#t-replacecond.

        :param list orders: A list of orders and their parameters.
        :param max_in_parallel: The number of requests to be sent in parallel.
            Note that you are limited to 50 requests per second.
        :returns: Future request result dictionaries as a list.
        """

        res = await self._sem_gather(
            max_in_parallel,
            *[self.replace_conditional_order(**order) for order in orders]
        )
        return [r for r in res]

    async def query_conditional_order(self, **kwargs):
        """
        Query real-time conditional order information.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-querycond.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['query_conditional_order'],
            query=kwargs,
            auth=True
        )

    async def my_position(self, **kwargs):
        """
        Get my position list.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-myposition.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['my_position'],
            query=kwargs,
            auth=True
        )

    async def set_auto_add_margin(self, **kwargs):
        """
        For linear markets only. Set auto add margin, or Auto-Margin
        Replenishment.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/linear/#t-setautoaddmargin.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['set_auto_add_margin'],
            query=kwargs,
            auth=True
        )

    async def set_leverage(self, **kwargs):
        """
        Change user leverage.

        If you want to switch between cross margin and isolated margin, please
        see cross_isolated_margin_switch.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/linear/#t-setleverage.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['set_leverage'],
            query=kwargs,
            auth=True
        )

    async def cross_isolated_margin_switch(self, **kwargs):
        """
        Switch Cross/Isolated; must be leverage value when switching from Cross
        to Isolated.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-marginswitch.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['cross_isolated_margin_switch'],
            query=kwargs,
            auth=True
        )

    async def query_trading_fee_rate(self, **kwargs):
        """
        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-queryfeerate.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['query_trading_fee_rate'],
            query=kwargs,
            auth=True
        )

    async def position_mode_switch(self, **kwargs):
        """
        If you are in One-Way Mode, you can only open one position on Buy or
        Sell side;
        If you are in Hedge Mode, you can open both Buy and Sell side positions
        simultaneously.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-switchpositionmode.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['position_mode_switch'],
            query=kwargs,
            auth=True
        )

    async def full_partial_position_tp_sl_switch(self, **kwargs):
        """
        Switch mode between Full or Partial
        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-switchmode.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['full_partial_position_tp_sl_switch'],
            query=kwargs,
            auth=True
        )

    async def change_margin(self, **kwargs):
        """
        Update margin.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-changemargin.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['change_margin'],
            query=kwargs,
            auth=True
        )

    async def set_trading_stop(self, **kwargs):
        """
        Set take profit, stop loss, and trailing stop for your open position.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-tradingstop.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['set_trading_stop'],
            query=kwargs,
            auth=True
        )

    async def add_reduce_margin(self, **kwargs):
        """
        For linear markets only. Add margin.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/linear/#t-addmargin.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['add_reduce_margin'],
            query=kwargs,
            auth=True
        )

    async def change_user_leverage(self, **kwargs):
        """
        Change user leverage.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-changeleverage.
        :returns: Request results as dictionary.
        """

        self.logger.warning('This endpoint is deprecated and will be removed. Use set_leverage()')

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['change_user_leverage'],
            query=kwargs,
            auth=True
        )

    async def user_trade_records(self, **kwargs):
        """
        Get user's trading records. The results are ordered in ascending order
        (the first item is the oldest).

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-usertraderecords.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['user_trade_records'],
            query=kwargs,
            auth=True
        )

    async def closed_profit_and_loss(self, **kwargs):
        """
        Get user's closed profit and loss records. The results are ordered in
        descending order (the first item is the latest).

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-closedprofitandloss.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['closed_profit_and_loss'],
            query=kwargs,
            auth=True
        )

    async def get_risk_limit(self, **kwargs):
        """
        Get risk limit.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-getrisklimit.
        :returns: Request results as dictionary.
        """

        if kwargs.get('is_linear') in (False, True):
            self.logger.warning("The is_linear argument is obsolete.")

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['get_risk_limit'],
            query=kwargs,
            auth=True
        )

    async def set_risk_limit(self, **kwargs):
        """
        Set risk limit.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-setrisklimit.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['set_risk_limit'],
            query=kwargs,
            auth=True
        )

    async def get_the_last_funding_rate(self, **kwargs):
        """
        The funding rate is generated every 8 hours at 00:00 UTC, 08:00 UTC and
        16:00 UTC. For example, if a request is sent at 12:00 UTC, the funding
        rate generated earlier that day at 08:00 UTC will be sent.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-fundingrate.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['get_the_last_funding_rate'],
            query=kwargs
        )

    async def my_last_funding_fee(self, **kwargs):
        """
        Funding settlement occurs every 8 hours at 00:00 UTC, 08:00 UTC and
        16:00 UTC. The current interval's fund fee settlement is based on the
        previous interval's fund rate. For example, at 16:00, the settlement is
        based on the fund rate generated at 8:00. The fund rate generated at
        16:00 will be used at 0:00 the next day.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-mylastfundingfee.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['my_last_funding_fee'],
            query=kwargs,
            auth=True
        )

    async def predicted_funding_rate(self, **kwargs):
        """
        Get predicted funding rate and my funding fee.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-predictedfunding.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['predicted_funding_rate'],
            query=kwargs,
            auth=True
        )

    async def api_key_info(self):
        """
        Get user's API key info.

        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['api_key_info'],
            auth=True
        )

    async def lcp_info(self, **kwargs):
        """
        Get user's LCP (data refreshes once an hour). Only supports inverse
        perpetual at present. See
        https://bybit-exchange.github.io/docs/inverse/#t-liquidity to learn
        more.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-lcp.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['lcp_info'],
            query=kwargs,
            auth=True
        )

    async def get_wallet_balance(self, **kwargs):
        """
        Get wallet balance info.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-balance.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['get_wallet_balance'],
            query=kwargs,
            auth=True
        )

    async def wallet_fund_records(self, **kwargs):
        """
        Get wallet fund records. This endpoint also shows exchanges from the
        Asset Exchange, where the types for the exchange are
        ExchangeOrderWithdraw and ExchangeOrderDeposit.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-walletrecords.
        :returns: Request results as dictionary.
        """

        # Replace query param 'from_id' since 'from' keyword is reserved.
        # Temporary workaround until Bybit updates official request params
        if 'from_id' in kwargs:
            kwargs['from'] = kwargs.pop('from_id')

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['wallet_fund_records'],
            query=kwargs,
            auth=True
        )

    async def withdraw_records(self, **kwargs):
        """
        Get withdrawal records.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-withdrawrecords.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['withdraw_records'],
            query=kwargs,
            auth=True
        )

    async def asset_exchange_records(self, **kwargs):
        """
        Get asset exchange records.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/inverse/#t-assetexchangerecords.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['asset_exchange_records'],
            query=kwargs,
            auth=True
        )

    async def server_time(self):
        """
        Get Bybit server time.

        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['server_time']
        )

    async def announcement(self):
        """
        Get Bybit OpenAPI announcements in the last 30 days by reverse order.

        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['announcement']
        )

    '''
    Additional Methods
    These methods use two or more requests to perform a specific
    function and are exclusive to pybit.
    '''

    async def close_position(self, symbol):
        """
        Closes your open position. Makes two requests (position, order).

        Parameters
        ------------------------
        symbol : str
            Required parameter. The symbol of the market as a string,
            e.g. 'BTCUSD'.

        """

        # First we fetch the user's position.
        try:
            r = (await self.my_position(symbol=symbol))['result']

        # If there is no returned position, we want to handle that.
        except KeyError:
            return self.logger.error('No position detected.')

        # Next we generate a list of market orders
        orders = [
            {
                'symbol': symbol,
                'order_type': 'Market',
                'side': 'Buy' if p['side'] == 'Sell' else 'Sell',
                'qty': p['size'],
                'time_in_force': 'ImmediateOrCancel',
                'reduce_only': True,
                'close_on_trigger': True,
                'position_idx': p['position_idx']
            } for p in (r if isinstance(r, list) else [r]) if p['size'] > 0
        ]

        if len(orders) == 0:
            return self.logger.error('No position detected.')

        # Submit a market order against each open position for the same qty.
        return await self.place_active_order_bulk(orders)

    '''
    Below are methods under https://bybit-exchange.github.io/docs/account_asset
    '''

    async def create_internal_transfer(self, **kwargs):
        """
        Create internal transfer.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/account_asset/#t-createinternaltransfer.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['create_internal_transfer'],
            query=kwargs,
            auth=True
        )

    async def create_subaccount_transfer(self, **kwargs):
        """
        Create internal transfer.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/account_asset/#t-createsubaccounttransfer.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='POST',
            path=self.url + self.endpoints['create_subaccount_transfer'],
            query=kwargs,
            auth=True
        )

    async def query_transfer_list(self, **kwargs):
        """
        Create internal transfer.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/account_asset/#t-querytransferlist.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['query_transfer_list'],
            query=kwargs,
            auth=True
        )

    async def query_subaccount_list(self):
        """
        Create internal transfer.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/account_asset/#t-querysubaccountlist.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['query_subaccount_list'],
            query={},
            auth=True
        )

    async def query_subaccount_transfer_list(self,**kwargs):
        """
        Create internal transfer.

        :param kwargs: See
            https://bybit-exchange.github.io/docs/account_asset/#t-querysubaccounttransferlist.
        :returns: Request results as dictionary.
        """

        return await self._submit_request(
            method='GET',
            path=self.url + self.endpoints['query_subaccount_transfer_list'],
            query=kwargs,
            auth=True
        )

    '''
    Internal methods; signature and request submission.
    For more information about the request signature, see
    https://bybit-exchange.github.io/docs/inverse/#t-authentication.
    '''

    def _auth(self, method, params, recv_window):
        """
        Generates authentication signature per Bybit API specifications.

        Notes
        -------------------
        Since the POST method requires a JSONified dict, we need to ensure
        the signature uses lowercase booleans instead of Python's
        capitalized booleans. This is done in the bug fix below.

        """

        api_key = self.api_key
        api_secret = self.api_secret

        if api_key is None or api_secret is None:
            raise PermissionError('Authenticated endpoints require keys.')

        # Append required parameters.
        params['api_key'] = api_key
        params['recv_window'] = recv_window
        params['timestamp'] = int(time.time() * 10 ** 3)

        # Sort dictionary alphabetically to create querystring.
        _val = '&'.join(
            [str(k) + '=' + str(v) for k, v in sorted(params.items()) if
             (k != 'sign') and (v is not None)]
        )

        # Bug fix. Replaces all capitalized booleans with lowercase.
        if method == 'POST':
            _val = _val.replace('True', 'true').replace('False', 'false')

        # Return signature.
        return str(hmac.new(
            bytes(api_secret, 'utf-8'),
            bytes(_val, 'utf-8'), digestmod='sha256'
        ).hexdigest())

    async def _submit_request(self, method=None, path=None, query=None, auth=False):
        """
        Submits the request to the API.

        Notes
        -------------------
        We use the params argument for the GET method, and json argument for
        the POST method. Dicts passed to the json argument are automatically
        JSONified, by ClientSession handler, prior to submitting request.

        """

        # Store original recv_window.
        recv_window = self.recv_window

        # Bug fix: change floating whole numbers to integers to prevent
        # auth signature errors.
        if query is not None:
            for i in query.keys():
                if isinstance(query[i], float) and query[i] == int(query[i]):
                    query[i] = int(query[i])

        # Send request and return headers with body. Retry if failed.
        retries_attempted = self.max_retries
        req_params = None

        while True:

            retries_attempted -= 1
            if retries_attempted < 0:
                raise FailedRequestError(
                    request=f'{method} {path}: {req_params}',
                    message='Bad Request. Retries exceeded maximum.',
                    status_code=400,
                    time = time.strftime("%H:%M:%S", time.gmtime())
                )

            retries_remaining = f'{retries_attempted} retries remain.'

            # Authenticate if we are using a private endpoint.
            if auth:

                # Prepare signature.
                signature = self._auth(
                    method=method,
                    params=query,
                    recv_window=recv_window,
                )

                # Sort the dictionary alphabetically.
                query = dict(sorted(query.items(), key=lambda x: x))

                # Append the signature to the dictionary.
                query['sign'] = signature

            # Define parameters and log the request.
            if query is not None:
                req_params = {k: v for k, v in query.items() if
                              v is not None}

            else:
                req_params = {}

            # Log the request.
            if self.log_requests:
                self.logger.info(f'Request -> {method} {path}: {req_params}')

            # Prepare request; use 'params' for GET and 'json' for POST.
            r = {'headers': self.headers}

            if method == 'GET':
                r['params'] = req_params
            else:
                if self.contract_type == 'spot':
                    full_param_str = '&'.join(
                        [str(k) + '=' + str(v) for k, v in
                         sorted(query.items()) if v is not None]
                    )
                    path += f"?{full_param_str}"
                else:
                    r['headers']['Content-Type'] = 'application/json'
                    r['json'] = req_params

            # Attempt the request.
            try:
                async with self.session.request(
                    method, path, **r, timeout=self.timeout
                ) as s:

                    # Convert response to dictionary, or raise if requests error.
                    try:
                        s_json = await s.json()

                    # If we have trouble converting, handle the error and retry.
                    except aiohttp.client_exceptions.ContentTypeError as e:
                        if self.force_retry:
                            self.logger.error(f'{e}. {retries_remaining}')
                            await asyncio.sleep(self.retry_delay)
                            continue
                        else:
                            raise FailedRequestError(
                                request=f'{method} {path}: {req_params}',
                                message='Conflict. Could not decode JSON.',
                                status_code=409,
                                time = time.strftime("%H:%M:%S", time.gmtime())
                            )

            # If requests fires an error, retry.
            except (
                aiohttp.client_exceptions.ClientConnectorError,
                aiohttp.client_exceptions.ServerConnectionError
            ) as e:
                if self.force_retry:
                    self.logger.error(f'{e}. {retries_remaining}')
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    raise e

            # If Bybit returns an error, raise.
            if s_json['ret_code']:

                # Generate error message.
                error_msg = (
                    f'{s_json["ret_msg"]} (ErrCode: {s_json["ret_code"]})'
                )

                # Set default retry delay.
                err_delay = self.retry_delay

                # Retry non-fatal whitelisted error requests.
                if s_json['ret_code'] in self.retry_codes:

                    # 10002, recv_window error; add 2.5 seconds and retry.
                    if s_json['ret_code'] == 10002:
                        error_msg += '. Added 2.5 seconds to recv_window'
                        recv_window += 2500

                    # 10006, ratelimit error; wait until rate_limit_reset_ms
                    # and retry.
                    elif s_json['ret_code'] == 10006:
                        self.logger.error(
                            f'{error_msg}. Ratelimited on current request. '
                            f'Sleeping, then trying again. Request: {path}'
                        )

                        # Calculate how long we need to wait.
                        limit_reset = s_json['rate_limit_reset_ms'] / 1000
                        reset_str = time.strftime(
                            "%X", time.localtime(limit_reset)
                        )
                        err_delay = int(limit_reset) - int(time.time())
                        error_msg =(
                            f'Ratelimit will reset at {reset_str}. '
                            f'Sleeping for {err_delay} seconds'
                        )

                    # Log the error.
                    self.logger.error(f'{error_msg}. {retries_remaining}')
                    await asyncio.sleep(err_delay)
                    continue

                elif s_json['ret_code'] in self.ignore_codes:
                    pass

                else:
                    raise InvalidRequestError(
                        request=f'{method} {path}: {req_params}',
                        message=s_json["ret_msg"],
                        status_code=s_json["ret_code"],
                        time=time.strftime("%H:%M:%S", time.gmtime())
                    )
            else:
                return s_json


class WebSocket:
    """
    Connector for Bybit's WebSocket API.

    :param session: Required parameter. An aiohttp ClientSession constructed
        session instance.
    :param endpoint: Required parameter. The endpoint of the remote
        websocket.
    :param api_key: Your API key. Required for authenticated endpoints.
        Defaults to None.
    :param api_secret: Your API secret key. Required for authenticated
        endpoints. Defaults to None.
    :param subscriptions: A list of desired topics to subscribe to. See API
        documentation for more information. Defaults to an empty list, which
        will raise an error if not spot private connection.
    :param logging_level: The logging level of the built-in logger. Defaults
        to logging.INFO. Options are CRITICAL (50), ERROR (40),
        WARNING (30), INFO (20), DEBUG (10), or NOTSET (0).
    :param ping_interval: The number of seconds between each automated ping.
        Pong timeout is based on ping_interval/2.
    :param restart_on_error: Whether or not the connection should restart on
        error.
    :param error_cb_func: Callback function to bind to exception error
        handling.

    :returns: WebSocket session.
    """

    def __init__(self, session, endpoint, api_key=None, api_secret=None,
                 subscriptions=None, logging_level='INFO', ping_interval=20,
                 restart_on_error=True, error_cb_func=None):

        """
        Initializes the websocket session.

        """

        # Set contract type
        self.contract_type = self._set_contract_type(endpoint)

        # Validate subscriptions
        if not subscriptions:
            if self.contract_type == 'spot_private':
                subscriptions = [
                    'outboundAccountInfo',
                    'executionReport',
                    'ticketInfo'
                ]
            else:
                raise Exception('Subscription list cannot be empty!')

        elif self.contract_type == 'spot_public' and api_key:
                raise Exception('Public topics do not require authentication!')

        # Validate some required parameters until Bybit docs are updated.
        if self.contract_type == 'derivatives':

            # Require symbol on 'trade' topic.
            if 'trade' in subscriptions:
                raise Exception('\'trade\' requires a ticker, e.g. '
                                '\'trade.BTCUSD\'.')

            # Require currency on 'insurance' topic.
            if 'insurance' in subscriptions:
                raise Exception('\'insurance\' requires a currency, e.g. '
                                '\'insurance.BTC\'.')

            # Require symbol on 'liquidation' topic.
            if 'liquidation' in subscriptions:
                raise Exception('\'liquidation\' requires a ticker, e.g. '
                                '\'liquidation.BTCUSD\'.')

            # Ensure authentication for private topics.
            if any(i in subscriptions for i in [
                'position',
                'execution',
                'order',
                'stop_order',
                'wallet'
            ]) and api_key is None:
                raise PermissionError('You must be authorized to use '
                                      'private topics!')

        # set websocket name for logging purposes
        self.wsName = 'Authenticated' if api_key else 'Non-Authenticated'

        # Setup logger.
        self.logger = LOGGER
        self.logger.info(f'Initializing {self.wsName} WebSocket.')

        # Set aiohttp client session.
        self.session = session

        # Set endpoint.
        self.endpoint = endpoint

        # Set API keys.
        self.api_key = api_key
        self.api_secret = api_secret

        # Set topic subscriptions for WebSocket.
        self.subscriptions = subscriptions

        # Set ping settings.
        self.ping_interval = ping_interval

        # Other optional data handling settings.
        self.handle_error = restart_on_error

        # Initialize handlers dictionary
        self.handlers = {}

        # Bind error handler callback function
        if error_cb_func:
            self.bind('error_cb', error_cb_func)

        # Set initial state, initialize dictionary and connect.
        self._reset()

    @staticmethod
    def _set_contract_type(endpoint: str):
        if 'spot' in endpoint:
            if any(i in endpoint for i in {'v1', 'v2'}):
                return 'spot_public'
            else:
                return 'spot_private'
        else:
            return 'derivatives'

    async def ping(self):
        """
        Pings the remote server to test the connection. The status of the
        connection can be monitored using ws.ping().
        """

        await self.ws.send_json({'op': 'ping'})

    async def exit(self):
        """
        Closes the websocket connection.
        """

        if self.ws:
            await self.ws.close()
        self.exited = True
        self.ws = None

    async def _auth(self):
        """
        Authorize websocket connection.
        """

        # Generate expires.
        expires = int((time.time() + 1) * 1000)

        # Generate signature.
        _val = f'GET/realtime{expires}'
        signature = str(hmac.new(
            bytes(self.api_secret, 'utf-8'),
            bytes(_val, 'utf-8'), digestmod='sha256'
        ).hexdigest())

        # Authenticate with API.
        await self.ws.send_json({
            'op': 'auth',
            'args': [self.api_key, expires, signature]
        })

    async def _connect(self):
        """
        Open websocket in a thread.
        """

        # Attempt to connect for X seconds.
        retries = 10
        while retries > 0:

            # Connect to WebSocket.
            try:
                self.ws = await self.session.ws_connect(
                    self.endpoint,
                    heartbeat=self.ping_interval
                )
                self._on_open()

            # Handle errors during connection phase.
            except(
                aiohttp.client_exceptions.WSServerHandshakeError,
                aiohttp.client_exceptions.ClientConnectorError
            ) as e:
                self.logger.error(
                    f'WebSocket connection {e!r}'
                )
                retries -= 1
 
                # If connection was not successful, raise error.
                if retries <= 0:
                    raise WebSocketException(e)

            else:
                break

            await asyncio.sleep(1)

        # If given an api_key, authenticate.
        if self.api_key and self.api_secret:
            await self._auth()

        # Subscribe to websocket topics.
        await self._subscribe()

    async def _subscribe(self):
        """
        Subscribe to websocket topics.
        """

        # Check if subscriptions is a list.
        if isinstance(self.subscriptions, (str, dict)):
            self.subscriptions = [self.subscriptions]

        # Subscribe to the requested topics.
        if self.contract_type == 'spot_public':
            for s in self.subscriptions:
                self.logger.debug(f"Subscribing to {self.spot_topic(s)} {s}.")
                await self.ws.send_json(s)

        elif self.contract_type == 'derivatives':
            await self.ws.send_json({
                'op': 'subscribe',
                'args': self.subscriptions
            })

    async def _heartbeat(self):
        while 1:
            await asyncio.sleep(self.ping_interval)
            self.ws._send_heartbeat()

    async def _dispatch(self):

        if self.contract_type == 'spot_public':
            consume = self._consume_spot_public
        elif self.contract_type == 'spot_private':
            consume = self._consume_spot_private
        else:
            consume = self._consume_derivatives

        while True:
            msg = await self.ws.receive()

            if msg.type == aiohttp.WSMsgType.TEXT:
                await consume(json.loads(msg.data))

            elif msg.type == aiohttp.WSMsgType.ERROR:
                raise WebSocketException(f'WebSocket connection error. Code: {self.ws.close_code}; {msg}')

            # Handle EofStream (type 257, etc)
            elif msg.type in (
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.CLOSING,
                aiohttp.WSMsgType.CLOSED
            ):
                raise WebSocketException(f'WebSocket connection closed. Code: {self.ws.close_code}; {msg}')

    async def _consume_derivatives(self, msg: dict):
        """
        Consumer to parse and emit incoming derivatives messages.
        """

        if 'topic' in msg:
            await self._emit(msg['topic'], msg)

        elif 'success' in msg:
            if msg['success']:
                # If 'request' exists.
                if 'request' in msg:
                    if msg['request']['op'] == 'auth':
                        self.logger.info('Authorization successful.')

                    elif msg['request']['op'] == 'subscribe':
                        topic = msg['request']['args']
                        self._on_subscribe(topic)

            else:
                if msg['request']['op'] == 'subscribe':
                    raise WebSocketException(f'Couldn\'t subscribe to topic.'
                                             f'Error: {msg["ret_msg"]}.')

                elif msg['request']['op'] == 'auth':
                    raise PermissionError('Authorization failed. Please '
                                          'check your API keys and restart.')

    async def _consume_spot_public(self, msg: dict):
        """
        Consumer to parse and emit incoming spot public messages.
        """

        # Spotv2 subscribe msg also has topic key, so we check it before topic.
        if 'msg' in msg and msg['msg'] == 'Success':
                topic = self.spot_topic(msg)
                self._on_subscribe(topic)

        elif 'topic' in msg:
            topic = self.spot_topic(msg)
            await self._emit(topic, msg)

        # Subscribe error msg
        elif 'code' in msg:
            if msg['code'] != '0':
                raise WebSocketException('Couldn\'t subscribe to topic. '
                                         f'Error {msg["code"]}: {msg["desc"]}.')

    async def _consume_spot_private(self, msg):
        """
        Consumer to parse and emit incoming spot private messages.
        """

        # topic
        if isinstance(msg, list):
            for m in msg:
                await self._emit(m['e'], m)

        elif 'auth' in msg:
            if msg['auth'] == 'success':
                self.logger.info('Authorization successful.')

                for topic in self.subscriptions:
                    self._on_subscribe(topic)

            else:
                raise PermissionError('Authorization failed. Please '
                                      'check your API keys and restart.')

        elif 'ping' in msg:
            pass

    @staticmethod
    def spot_topic(msg: dict):
        """
        Generate spot public topics to match common derivates format:
        [topic][spot version][.][klineType|dumpScale value][.][symbol]
        eg. klineV1.1m.BTCUSDT, tradeV2.BTCUSDT, mergedDepthV1.1.BTCUSDT

        :param msg: Dict with parsed json, in subscription or received
            message format.

        :returns: Formatted topic as str.
        """

        try:
            # Spot version.
            topic = msg['topic'] + ('V1' if 'symbol' in msg else 'V2')

            # Params values. realtimeV1 topic does not have params.
            if 'params' in msg:
                # kline; v1/v2
                if 'klineType' in msg['params']:
                    topic += f".{msg['params']['klineType']}"

                # mergedDepth; v1 only
                elif 'dumpScale' in msg['params']:
                    topic += f".{msg['params']['dumpScale']}"

            # Symbol; v1|v2
            if 'symbol' in msg:
                topic += f".{msg['symbol']}"
            else:
                topic += f".{msg['params']['symbol']}"

            return topic

        except KeyError as e:
            raise KeyError(f'{e} missing in {msg}')

    async def _emit(self, topic: str, msg):
        """
        Send message data events to binded callback functions.

        :param topic: Required. Subscription topic.
        :param msg: Required. Message event json data.
        """
        await self.handlers[topic](msg)

    def bind(self, topic, func):
        """
        Bind functions by topic to local object to handle websocket message events.

        :param topic: Required. Subscription topic.
        :param func: Required. Callback Function to handle processing of events.
        """
        if not asyncio.iscoroutinefunction(func):
            raise ValueError(f'Binded handler {func} must be coroutine function!')

        # Bind function handler to topic events.
        self.handlers[topic] = func

    def unbind(self, topic):
        """
        UnBind functions from local websocket message events.

        :param topic: Required. Subscription topic.
        """
        del self.handlers[topic]

    async def _on_error(self, error):
        """
        Exit on errors and raise exception, or attempt reconnect.
        """

        t = time.strftime("%H:%M:%S", time.gmtime())
        self.logger.error(
            f'WebSocket {self.wsName} encountered a {error!r} (ErrTime: {t} UTC).'
        )
        await self.exit()

        if 'error_cb' in self.handlers:
            await self._emit('error_cb', error)

        # Reconnect.
        if self.handle_error:
            self.logger.info(f'WebSocket {self.wsName} reconnecting.')
            self._reset()

    def _on_open(self):
        """
        Log WS open.
        """
        self.logger.info(f'WebSocket {self.wsName} opened.')

    async def _on_close(self):
        """
        Log WS close.
        """
        self.logger.info(f'WebSocket {self.wsName} closed.')
        await self.exit()

    def _on_subscribe(self, topic):
        """
        Log and store WS subscription successes.
        """
        self.logger.info(f'Subscription to {topic} successful.')
        self._subscribed.append(topic)

    @property
    def subscribed(self):
        return self._subscribed

    def _reset(self):
        """
        Set state booleans and initialize dictionary.
        """
        self.exited = False
        self.ws = None
        self._subscribed = []

    async def run_forever(self):
        self.logger.debug(f'WebSocket {self.wsName} starting stream.')

        while not self.exited:
            try:
                if not self.ws:
                    await self._connect()

                # Force ping to avoid anomolous Bybit closing on spot public
                if self.contract_type == 'spot_public':
                    await asyncio.gather(self._dispatch(), self._heartbeat())
                else:
                    await self._dispatch()

            except asyncio.CancelledError as e:
                self.logger.warning(f'Asyncio interrupt received.')
                self.exited = True
                break

            except WebSocketException as e:
                await self._on_error(e)

            except PermissionError as e:
                self.handle_error = False
                await self._on_error(e)

           finally:
                if self.exited:
                    await self._on_close()
                    break

            await asyncio.sleep(0.01)

import unittest, asyncio, aiohttp
from unittest.mock import AsyncMock, patch, MagicMock
from pybit import Exchange

REST_URL = 'https://api.bybit.com'
REST_CONTRACT_TYPE = 'linear'
WS_PUBLIC_URL = 'wss://stream.bybit.com/realtime'
SUBS = ['instrument_info.100ms.BTCUSD']

class TestSession:

    async def setUpREST(self):
        # Set up the real Exchange and HTTP chain
        self.exchange = Exchange()
        self.rest = self.exchange.rest(
            endpoint=REST_URL,
            contract_type=REST_CONTRACT_TYPE
        )

    async def setUpWebSocket(self):
        # Set up the real Exchange and WebSocket chain
        self.exchange = Exchange()
        self.ws = self.exchange.websocket(
            endpoint=WS_PUBLIC_URL,
            subscriptions=SUBS,
            restart_on_error=False
        )

    async def tearDown(self):
        await self.exchange.exit()

class HTTPTest(unittest.IsolatedAsyncioTestCase):
    """Test the HTTP class from pybit module"""

    session = TestSession()

    @classmethod
    def setUpClass(cls):
        asyncio.run(cls.session.setUpREST())
        cls._patcher = patch.object(cls.session.rest, '_submit_request')
        cls._mock_submit = cls._patcher.start()

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls.session.tearDown())
        cls._patcher.stop()

    async def asyncSetUp(self):
        self._mock_submit.reset_mock()
        self._mock_submit.return_value = None
        self._mock_submit.side_effect = None

    async def test_orderbook(self):
        self._mock_submit.return_value = {'ret_msg': 'OK'}
        result = await self.session.rest.orderbook(symbol='BTCUSD')
        self.assertEqual(result['ret_msg'], 'OK')

    async def test_query_kline(self):
        self._mock_submit.return_value = {'ret_msg': 'OK'}
        result = await self.session.rest.query_kline(
            symbol='BTCUSD', interval='1', from_time=123456789
        )
        self.assertEqual(result['ret_msg'], 'OK')

    async def test_latest_information_for_symbol(self):
        self._mock_submit.return_value = {'ret_msg': 'OK'}
        result = await self.session.rest.latest_information_for_symbol(symbol='BTCUSD')
        self.assertEqual(result['ret_msg'], 'OK')

    async def test_public_trading_records(self):
        self._mock_submit.return_value = {'ret_msg': 'OK'}
        result = await self.session.rest.public_trading_records(symbol='BTCUSD')
        self.assertEqual(result['ret_msg'], 'OK')

    async def test_query_symbol(self):
        self._mock_submit.return_value = {'ret_msg': 'OK'}
        result = await self.session.rest.query_symbol()
        self.assertEqual(result['ret_msg'], 'OK')

    async def test_server_time(self):
        self._mock_submit.return_value = {
            'ret_msg': 'OK',
            'result': {'timeSecond': 1234567890}
        }
        result = await self.session.rest.server_time()
        self.assertEqual(result['ret_msg'], 'OK')
        self.assertEqual(result['result']['timeSecond'], 1234567890)

    async def test_announcement(self):
        self._mock_submit.return_value = {
            'ret_msg': 'OK',
            'result': []
        }
        result = await self.session.rest.announcement()
        self.assertEqual(result['ret_msg'], 'OK')

    # We can't really test authenticated endpoints without keys, but we
    # can make sure it raises a PermissionError.
    async def test_place_active_order(self):
        self._mock_submit.side_effect = PermissionError()
        with self.assertRaises(PermissionError):
            result = await self.session.rest.place_active_order(
                symbol='BTCUSD', order_type='Market', side='Buy', qty=1
            )

class WebSocketTest(unittest.IsolatedAsyncioTestCase):
    """Test the WebSocket class from pybit module"""

    session = TestSession()

    @classmethod
    def setUpClass(cls):
        asyncio.run(cls.session.setUpWebSocket())
        cls.session.ws.bind(SUBS[0], cls.ws_callback)

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls.session.tearDown())

    async def ws_callback(msg):
        pass

    async def test_websocket(self):
        mock_ws = AsyncMock()
        mock_ws.receive.side_effect = [
            MagicMock(type=aiohttp.WSMsgType.TEXT, data='{"topic": "'+SUBS[0]+'", "action": "test1"}'),
            MagicMock(type=aiohttp.WSMsgType.TEXT, data='{"topic": "'+SUBS[0]+'", "action": "test2"}'),
            Exception('End of test')
        ]

        with patch.object(self.session.ws.session, 'ws_connect', new=AsyncMock(return_value=mock_ws)):
            with patch.object(self.session.ws, '_emit') as mock_emit:
                with self.assertRaises(Exception):
                    await self.session.ws.run_forever()

                call_args = mock_emit.call_args_list
                self.assertEqual(mock_emit.call_count, 2)
                self.assertEqual(call_args[0][0][1]['action'], 'test1')
                self.assertEqual(call_args[1][0][1]['action'], 'test2')

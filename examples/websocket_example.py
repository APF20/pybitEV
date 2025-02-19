"""
To see which endpoints and topics are available, check the Bybit API 
documentation: https://bybit-exchange.github.io/docs/inverse/#t-websocket

Inverse Perpetual endpoints:
wss://stream-testnet.bybit.com/realtime
wss://stream.bybit.com/realtime

USDT Perpetual endpoints:
wss://stream-testnet.bybit.com/realtime_public
wss://stream-testnet.bybit.com/realtime_private
wss://stream.bybit.com/realtime_public
wss://stream.bybit.com/realtime_private

Spot endpoints:
wss://stream-testnet.bybit.com/spot/quote/ws/v1
wss://stream-testnet.bybit.com/spot/quote/ws/v2
wss://stream-testnet.bybit.com/spot/ws
wss://stream.bybit.com/spot/quote/ws/v1
wss://stream.bybit.com/spot/quote/ws/v2
wss://stream.bybit.com/spot/ws

Futures Public Topics:
orderBookL2_25
orderBookL2-200
trade
insurance
instrument_info
klineV2
liquidation

Futures Private Topics:
position
execution
order
stop_order
wallet

Spot Public Topics:
Subscribing to spot public topics uses the JSON format to pass the topic name
and filters, as opposed to futures WS where the topic and filters are pass in
a single string. So, a python dict is required in your subscriptions.
Examples can be found in the code panel here:
https://bybit-exchange.github.io/docs/spot/#t-publictopics

Binding functions to the spot public topic streams uses canonical topic names!
See WebSocket().spot_topic() method and examples below for spot topic details.

Spot Private Topics:
Subscribing to spot private topics is done automatically upon authentication.
outboundAccountInfo
executionReport
ticketInfo
"""

# Import pybit and asyncio, define a coroutine and WebSocket object.
import asyncio
from pybit import Exchange

"""
We can also create a REST Exchange object at the same time using:

async with Exchange() as session:
    rest = session.rest(...)
    ws = session.websocket(...)
"""

# Define your endpoint URL and subscriptions.
endpoint = 'wss://stream.bybit.com/realtime'
subs = [
    'orderBookL2_25.BTCUSD',
    'instrument_info.100ms.BTCUSD',
    'instrument_info.100ms.ETHUSD'
]

async def main():
    # Create callback functions for events
    async def orderBook(msg):
        print(msg['topic'])
        print(msg['data'])

    async def instruments(msg):
        print(msg)

    async def position(msg):
        print(msg)
        
    async def onError(err):
        print(err)
 
    async with Exchange() as session:
        # Connect without authentication!
        ws = session.websocket(endpoint, subscriptions=subs)
        
        # Let's bind orderbook events to the orderBook function
        ws.bind('orderBookL2_25.BTCUSD', orderBook)
        
        # Let's bind all instrument events to the instruments function
        ws.bind('instrument_info.100ms.BTCUSD', instruments)
        ws.bind('instrument_info.100ms.ETHUSD', instruments)

        # Connect with authentication!
        ws_auth = session.websocket(
            endpoint,
            subscriptions=['position'],
            api_key='...',
            api_secret='...',
            error_cb_func=onError
        )

        # Bind position events stream to the position function.
        # Note that no position data is received until a change
        # in your position occurs (initially, there will be no data).
        ws_auth.bind('position', position)

        # Start the streaming events
        await asyncio.gather(
            ws.run_forever(),
            ws_auth.run_forever()
        )

asyncio.run(main())


# Define your Spot endpoint URL and subscriptions.
endpoint = 'wss://stream.bybit.com/spot/quote/ws/v2'
subs=[
    {
        'topic': 'depth',
        'params': {'symbol': 'ETHUSDT', 'binary': False},
        'event': 'sub'
    },
    {
        'topic': 'kline',
        'params': {'symbol': 'ETHUSDT', 'klineType': '1m', 'binary': False},
        'event': 'sub'
    }
]

async def main():
    # Create callback functions for events
    async def depth(msg):
        print(msg['topic'])
        print(msg['data'])

    async def kline(msg):
        print(msg)

    async with Exchange() as session:
        # Connect without authentication!
        ws = session.websocket(endpoint, subscriptions=subs)
        
        # Let's bind depth events to the depth function
        # ** Note the use of canonical topic names for binding!
        # See WebSocket().spot_topic() method for spot topic details.
        ws.bind('depthV2.ETHUSDT', depth)
        
        # Let's bind kline 1m events to the kline function
        ws.bind('klineV2.1m.ETHUSDT', kline)

        # Start the streaming events
        await ws.run_forever()

asyncio.run(main())

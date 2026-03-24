import unittest, asyncio, aiohttp
import pyngx
from unittest.mock import AsyncMock, patch, MagicMock, DEFAULT

REST_URL = 'https://open-api.bingx.com'
REST_CONTRACT_TYPE = 'usd_futures'
WS_PUBLIC_URL = 'wss://open-api-swap.bingx.com/swap-market'
SUBS = ['BTC-USDT@bookTicker']


class TestSession:

    async def setUpREST(self):
        """Set up the real Exchange and HTTP chain"""
        self.exchange = pyngx.Exchange()
        self.rest = self.exchange.rest(
            endpoint=REST_URL,
            contract_type=REST_CONTRACT_TYPE
        )

    async def setUpWebSocket(self):
        """Set up the real Exchange and WebSocket chain"""
        self.exchange = pyngx.Exchange()
        self.ws = self.exchange.websocket(
            endpoint=WS_PUBLIC_URL,
            subscriptions=SUBS,
            restart_on_error=False
        )

    async def tearDown(self):
        await self.exchange.exit()


class EndOfTestException(Exception):
    """Raised by mocks to signal test completion"""
    pass


class HTTPTest(unittest.IsolatedAsyncioTestCase):
    """Test the HTTP class from pyngx module"""

    session = TestSession()
    api_key = '1234567890'
    api_secret = 'abcdefghijkl'
    timestamp = 1234567890

    @classmethod
    def setUpClass(cls):
        asyncio.run(cls.session.setUpREST())

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls.session.tearDown())

    def test_set_contract_type(self):
        endpoint = ('get_quote_contracts', ('GET', False, 10, '/openApi/swap/v2/quote/contracts'))

        with patch.object(pyngx.endpoints.Endpoints, REST_CONTRACT_TYPE, new={endpoint[0]: endpoint[1]}):
            self.session.rest.set_contract_type(REST_CONTRACT_TYPE)
            self.assertEqual(self.session.rest.endpoints[endpoint[0]], endpoint[1])

    async def test_do(self):
        symbol = 'BTC-USDT'
        endpoint = ('get_quote_contracts', ('GET', False, 10, '/openApi/swap/v2/quote/contracts'))

        with patch.multiple(self.session.rest, endpoints={endpoint[0]: endpoint[1]}, _submit_request=DEFAULT) as mocks:
            await self.session.rest.do(endpoint[0], symbol=symbol)
            method, auth, limit, path = endpoint[1]
            mocks['_submit_request'].assert_called_once_with(
                method=method,
                path=path,
                query={'symbol': symbol},
                auth=auth
            )

    def test_auth(self):
        mock_args = {'symbol': 'BTC-USDT'}
        expected = {
            'timestamp': 1234567890000,
            'signature': '47d8b17d056a0cc9c35b7cdcf8a4448943a8773cfb88217b192c66dd0a1f72b9'
        }

        with(
            patch.multiple(self.session.rest, api_key=self.api_key, api_secret=self.api_secret),
            patch.object(pyngx.time, 'time', return_value=self.timestamp)
        ):
            result = self.session.rest._auth(mock_args)
            self.assertEqual(result['timestamp'], expected['timestamp'])
            self.assertEqual(result['signature'], expected['signature'])

    async def test_submit_request(self):
        path = '/openApi/swap/v2/quote/contracts'
        query = {'symbol': 'BTCUSDT'}
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        auth_headers = headers | {'X-BX-APIKEY': self.api_key}

        cases = [
            {
                'name': 'get',
                'method': 'GET',
                'auth': False,
                'response': {'code': 0},
                'expected': headers
            },
            {
                'name': 'post',
                'method': 'POST',
                'auth': False,
                'response': {'code': 0},
                'expected': headers
            },
            {
                'name': 'auth',
                'method': 'GET',
                'auth': True,
                'response': {'code': 0},
                'expected': auth_headers
            },
            {
                'name': 'auth fail',
                'method': 'GET',
                'auth': True,
                'response': {'code': 100001, 'msg': 'auth fail'},
                'expected': PermissionError
            },
            {
                'name': 'json fail',
                'method': 'GET',
                'auth': False,
                'response': aiohttp.client_exceptions.ContentTypeError('test', 'fail'),
                'expected': pyngx.exceptions.FailedRequestError
            },
            {
                'name': 'client os fail',
                'method': 'GET',
                'auth': False,
                'response': aiohttp.client_exceptions.ClientOSError('fail'),
                'expected': aiohttp.client_exceptions.ClientOSError
            },
            {
                'name': 'server timeout fail',
                'method': 'GET',
                'auth': False,
                'response': aiohttp.client_exceptions.ServerTimeoutError('fail'),
                'expected': aiohttp.client_exceptions.ServerTimeoutError
            },
        ]

        for case in cases:

            with self.subTest(name=case['name']):

                patch_kwargs = {
                    'url': REST_URL,
                    'headers': headers,
                    'api_key': self.api_key,
                    '_auth': MagicMock(return_value=query)
                }

                with(
                    patch.multiple(self.session.rest, **patch_kwargs),
                    patch.object(self.session.rest.session, 'request') as mock_request
                ):
                    mock_request.return_value.__aenter__.return_value.json = AsyncMock(
                        side_effect=[case['response']]
                    )

                    is_exception = isinstance(case['expected'], type) and issubclass(case['expected'], BaseException)

                    # Execute
                    if is_exception:
                        with self.assertRaises(case['expected']):
                            await self.session.rest._submit_request(
                                case['method'], path, query=query, auth=case['auth']
                            )
                    else:
                        await self.session.rest._submit_request(
                            case['method'], path, query=query, auth=case['auth']
                        )

                    if case['auth']:
                        self.session.rest._auth.assert_called_once()

                    mock_request.assert_called_once()
                    args, kwargs = mock_request.call_args
                    self.assertEqual(args, (case['method'], f'{REST_URL}{path}'))

                    if not is_exception:
                        self.assertEqual(kwargs['headers'], case['expected'])

                        if case['method'] == 'POST':
                            self.assertEqual(kwargs['data'], pyngx.json.dumps(query).encode('utf-8'))
                        else:
                            self.assertEqual(kwargs['params'], query)

    async def test_full_chain_get_user_positions(self):
        symbol = 'BTC-USDT'
        endpoint = 'get_user_positions'
        expected_header = 'X-BX-APIKEY'
        expected_signature = '47d8b17d056a0cc9c35b7cdcf8a4448943a8773cfb88217b192c66dd0a1f72b9'

        cases = [
            {
                'name': 'success',
                'response': {'code': 0, 'data': [{'positionId': '123456789'}]},
                'exception': None
            },
            {
                'name': 'fail',
                'response': {'code': 1234, 'msg': 'failed request'},
                'exception': pyngx.exceptions.InvalidRequestError
            }
        ]

        for case in cases:

            with self.subTest(name=case['name']):
                response = AsyncMock()
                response.json = AsyncMock(return_value=case['response'])

                with(
                    patch.multiple(self.session.rest, api_key=self.api_key, api_secret=self.api_secret),
                    patch.object(pyngx.time, 'time', return_value=self.timestamp),
                    patch.object(self.session.rest.session, 'request') as mock_request
                ):
                    mock_request.return_value.__aenter__.return_value = response
                    mock_request.return_value.__aexit__.return_value = None

                    if case['exception']:
                        with self.assertRaises(case['exception']) as e:
                            await self.session.rest.do(endpoint, symbol=symbol)
                        self.assertEqual(e.exception.status_code, case['response']['code'])
                    else:
                        result = await self.session.rest.do(endpoint, symbol=symbol)
                        self.assertEqual(result, case['response'])

                    _, kwargs = mock_request.call_args
                    self.assertIn(expected_header, kwargs['headers'])
                    self.assertEqual(kwargs['headers'][expected_header], self.api_key)
                    self.assertEqual(kwargs['params']['signature'], expected_signature)

    async def test_full_chain_auth_fail(self):
        """
        We can't really test full-chain authenticated endpoints without keys,
        but we can make sure it raises a PermissionError.
        """
        endpoint = 'post_trade_order'
        mock_kwargs = {'symbol': 'BTC-USD', 'order_type': 'MARKET', 'side': 'BUY', 'positionSide': 'LONG', 'qty': 1}

        with patch.object(self.session.rest.session, 'request', PermissionError()) as mock_request:
            with self.assertRaises(PermissionError):
                await self.session.rest.do(endpoint, **mock_kwargs)


class WebSocketTest(unittest.IsolatedAsyncioTestCase):
    """Test the WebSocket class from pyngx module"""

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

    def _gzip_compress_bytes(self, bytes_data):
        compressor = pyngx.zlib.compressobj(wbits=31)
        return compressor.compress(bytes_data) + compressor.flush()

    async def test_websocket(self):
        payloads = (
            self._gzip_compress_bytes(f'{{"code": 0, "dataType": "{SUBS[0]}", "data": "test1"}}'.encode()),
            self._gzip_compress_bytes(f'{{"code": 0, "dataType": "{SUBS[0]}", "data": "test2"}}'.encode())
        )

        mock_ws = AsyncMock()
        mock_ws.receive.side_effect = [
            MagicMock(type=aiohttp.WSMsgType.BINARY, data=payloads[0]),
            MagicMock(type=aiohttp.WSMsgType.BINARY, data=payloads[1]),
            EndOfTestException('End of test')
        ]

        with patch.object(self.session.ws.session, 'ws_connect', new=AsyncMock(return_value=mock_ws)):
            with patch.object(self.session.ws, '_emit') as mock_emit:
                with self.assertRaises(EndOfTestException):
                    await self.session.ws.run_forever()

                self.assertEqual(mock_emit.call_count, 2)
                call_args = mock_emit.call_args_list
                self.assertEqual(call_args[0][0][1]['data'], 'test1')
                self.assertEqual(call_args[1][0][1]['data'], 'test2')

"""
pyngx
------------------------

pyngx is a lightweight, rate-limit aware, high-performance and asyncronous
API connector for the RESTful and WebSocket APIs of the Bingx exchange.

Documentation can be found at
https://github.com/APF20/pyngx

:copyright: (c) 2023 APF20

:license: MIT License

"""

import time
import hmac
import asyncio
import aiohttp
import json
import zlib

from .exceptions import FailedRequestError, InvalidRequestError, WebSocketException
from .endpoints import Endpoints
from .log import Logger
from .ratelimit import RateLimiter
from .constants import REST_URL, WS_LISTEN_KEY_URL

# VERSION = '3.6.0'


class Exchange:
    """
    Exchange Interface for pyngx REST and WebSocket API
    """

    def __init__(self, logger=None):
        """
        :param obj logger: An initialised logging object.
        """

        self.session = aiohttp.ClientSession()
        self.logger = logger if logger else Logger().setup_custom_logger('root', streamLevel='INFO')

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
        Create REST Object.

        :param kwargs: See REST Class.
        :returns: REST Object.
        """
        return REST(self.session, logger=self.logger, **kwargs)

    def websocket(self, endpoint, **kwargs):
        """
        Create WebSocket Object.

        :param str endpoint: Required parameter. The endpoint of the remote
            websocket.
        :param kwargs: See WebSocket Class.
        :returns: REST WebSocket Object.
        """
        return WebSocket(self.session, self.logger, endpoint, **kwargs)

    @property
    def clientSession(self):
        return self.session

    @property
    def exchangeLogger(self):
        return self.logger


class REST:
    """
    Connector for Bingx's REST API.

    :param obj session: Required parameter. An aiohttp ClientSession constructed
        session instance.
    :param obj logger: Required parameter. An initialised logging object.
    :param str endpoint: The base endpoint URL of the REST API, e.g.
        'https://open-api.bingx.com'.
    :param str api_key: Your API key. Required for authenticated endpoints. Defaults
        to None.
    :param str api_secret: Your API secret key. Required for authenticated
        endpoints. Defaults to None.
    :param Union[int, logging.level] logging_level: The logging level of the built-in
        logger. Defaults to logging.INFO. Options are CRITICAL (50), ERROR (40),
        WARNING (30), INFO (20), DEBUG (10), or NOTSET (0).
    :param bool log_requests: Whether or not pyngx should log each REST request.
    :param int request_timeout: The timeout of each REST request in seconds. Defaults
        to 10 seconds.
    :param bool force_retry: Whether or not pyngx should retry a timed-out request.
    :param set retry_codes: A list of non-fatal status codes to retry on.
    :param set ignore_codes: A list of non-fatal status codes to ignore.
    :param int max_retries: The number of times to re-attempt a request.
    :param int retry_delay: Seconds between retries for returned error or timed-out
        requests. Default is 2 seconds.
    :param str contract_type: The contract type endpoints to use for requests. e.g.
        'usd_futures', 'spot', 'standard', 'account', 'sub_account'. Can be dynamically
        changed by using set_contract_type().

    :returns: pyngx.REST session.
    """

    def __init__(self, session, logger, *, endpoint=None, api_key=None, api_secret=None,
                 passphrase=None, logging_level='INFO', log_requests=False,
                 request_timeout=10, force_retry=False, retry_codes=None,
                 ignore_codes=None, max_retries=3, retry_delay=2,
                 contract_type=None):

        """Initializes the REST class."""

        # Set the base endpoint url.
        self.url = REST_URL if not endpoint else endpoint

        # Setup logger.
        self.logger = logger
        self.logger.info('Initializing pyngx REST session.')
        self.log_requests = log_requests

        # Validate API keys.
        if api_key and api_secret is None:
            raise PermissionError(
                'You must be authorized to use private interface!'
            )

        # Set API keys.
        self.api_key = api_key
        self.api_secret = api_secret

        # Set timeout to ClientTimeout sentinel.
        self.timeout = aiohttp.ClientTimeout(sock_read=request_timeout)
        self.force_retry = force_retry
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Set whitelist of non-fatal Bingx status codes to retry on.
        self.retry_codes = {
            429,      # request too frequent
            40029,    # request too frequent
            100410,   # rate limited
            100421,   # timestamp mismatch
            100500,   # internal system error
            100503,   # server busy
            80012     # service unavailable
        } if not retry_codes else retry_codes

        # Set whitelist of non-fatal Bingx status codes to ignore.
        self.ignore_codes = {} if not ignore_codes else ignore_codes

        # Set aiohttp client session.
        self.session = session

        # Set default aiohttp headers.
        self.headers = {
            'User-Agent': 'pyngx',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Set contract type
        self.set_contract_type(contract_type)

        # Initialize dict for rate limiters per endpoint.
        self.endpoint_limiters = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *err):
        await self.exit()

    async def exit(self):
        """Closes the aiohttp session."""
        await self.session.close()
        self.logger.info('REST session closed.')

    def set_contract_type(self, type: str):
        """
        Set contract_type var and endpoints dict based on contract type.

        :param str type: Contract type e.g. usd_futures, spot, standard,
            account, sub_account
        """

        if type:
            self.logger.info(f'Using {type} contract type endpoints.')
            self.endpoints = {**getattr(Endpoints, type)}

        else:
            self.endpoints = {}
            self.logger.warning(
                'Contract type is not set. Only account asset endpoints are available. '
                'Use contract_type init param or set_contract_type() to set/change.'
            )

        # add common endpoints
        self.endpoints.update(Endpoints.common)

    async def do(self, endpoint, **kwargs):
        """
        Perform REST API endpoint operations.

        :param kwargs: See
            https://bingx-api.github.io/docs/#/swapV2/introduce
        :returns: Request results as dictionary.
        """

        method, auth, limit, path = self.endpoints[endpoint]

        # Set ratelimiter
        try:
            rate_limiter = self.endpoint_limiters[path]
        except KeyError:
             # Initialize a new rate limiter for endpoint.
            self.endpoint_limiters[path] = RateLimiter(max_calls=limit, time_window=1.2)
            rate_limiter = self.endpoint_limiters[path]

        # Wait for any rate limit on this endpoint.
        async with rate_limiter.semaphore:
            await rate_limiter._wait_for_token()

            return await self._submit_request(
                method=method,
                path=path,
                query=kwargs,
                auth=auth
            )

    """
    Additional Methods
    These methods use requests to perform a specific
    function and are exclusive to pyngx.
    """

    async def batch_create_order(self, orders: list, max_in_parallel=10, return_exceptions=False):
        """
        Places multiple active orders in bulk using async concurrency. For more
        information on trade_order, see
        https://bingx-api.github.io/docs/#/swapV2/trade-api.html#Trade%20order

        :param list orders: A list of orders and their parameters.
        :param max_in_parallel: The number of requests to be sent in parallel.
            Note that you are limited to 500 requests per minute.
        :param return_exc: return exceptions as opposed to propagate
            for asyncio.gather in _sem_gather().
        :returns: Future request result dictionaries as a list.
        """

        res = await asyncio.gather(
            *[self.do('post_trade_order', **order) for order in orders],
            return_exceptions=return_exceptions
        )
        return [r for r in res]

    async def batch_cancel_order(self, orders: list, max_in_parallel=10, return_exceptions=False):
        """
        Cancels multiple active orders in bulk using async concurrency. For more
        information on trade_order, see
        https://bingx-api.github.io/docs/#/swapV2/trade-api.html#Cancel%20a%20Batch%20of%20Orders

        :param list orders: A list of orders and their parameters.
        :param max_in_parallel: The number of requests to be sent in parallel.
            Note that you are limited to 500 requests per minute.
        :returns: Future request result dictionaries as a list.
        """

        res = await asyncio.gather(
            *[self.do('delete_trade_order', **order) for order in orders],
            return_exceptions=return_exceptions
        )
        return [r for r in res]
        
    """
    Internal methods; signature and request submission.
    For more information about the request signature, see
    https://bingx-api.github.io/docs/#/swapV2/authentication.html#Signature
    """

    def _auth(self, params):
        """
        Generates authentication signature per Bingx API specifications.
        """

        api_key = self.api_key
        api_secret = self.api_secret

        if api_key is None:
            raise PermissionError('Authenticated endpoints require keys.')

        # Generate timestamp in milliseconds and append to dict.
        params['timestamp'] = int(time.time() * 1000)

        # Sort params alphabetically.
        params = dict(sorted(params.items()))

        # Generate payload str to sign from alphabetically sorted params.
        # Bug fix: change floating numbers that have 4 ~ 16 decimals from
        # scientific notation to str(float) to prevent auth signature errors.
        _val = '&'.join([
            f'{k}={f"{v:.16f}".rstrip("0") if isinstance(v, float) and abs(v) < 1e-4 else v}'
            for k, v in params.items()
        ])

        # Generate signature and append to dict.
        params['signature'] = hmac.new(
            api_secret.encode(),
            _val.encode(),
            digestmod='sha256'
        ).hexdigest()

        # return sorted and signed params dict.
        return params

    async def _submit_request(self, method, path, *, query=None, auth=False):
        """
        Submits the request to the API.

        Notes
        -------------------
        We use the params argument for the GET method, and data (bytes) argument
        for the POST/DELETE method. Dicts passed to the json argument are automatically
        JSONified, byte encoded and set to data argument, by ClientSession handler
        prior to submitting request.
        """

        # Define query parameters.
        if query:
            req_params = {k: v for k, v in query.items() if
                          v is not None}
        else:
            req_params = {}

        # Set default request headers.
        r = {'headers': self.headers}

        # Form absolute url.
        url = self.url + path

        # Send request and return headers with body. Retry if failed.
        retries_attempted = self.max_retries

        while True:

            retries_attempted -= 1
            if retries_attempted < 0:
                raise FailedRequestError(
                    request=f'{method} {url}: {req_params}',
                    message='Bad Request. Retries exceeded maximum.',
                    status_code=400,
                    time = time.strftime("%H:%M:%S", time.gmtime())
                )

            retries_remaining = f'{retries_attempted} retries remain.'

            # Authenticate if we are using a private endpoint.
            if auth:

                # Append api key to headers
                r['headers']['X-BX-APIKEY'] = self.api_key

                # Prepare sorted and signed request parameters.
                req_params = self._auth(params=req_params)

            # Prepare request; use 'params' for GET and b'data' for POST.
            if method == 'GET':
                r['params'] = req_params

            elif req_params:

                # JSONify body and encode to utf-8 bytes, per JsonPayload() of session.
                r['data'] = json.dumps(req_params).encode()

            # Log the request.
            if self.log_requests:
                self.logger.info(f'Request -> {method} {url}: {req_params}')

            # Attempt the request.
            try:
                async with self.session.request(
                    method, url, **r, timeout=self.timeout
                ) as s:

                    # Convert response to dictionary, or raise if requests error.
                    try:
                        s_json = await s.json()

                    # If we have trouble converting, handle the error and retry.
                    except aiohttp.client_exceptions.ContentTypeError as e:

                        # Check if we are rate limited. Response will be text/plain not json.
                        if s.status == 429:

                            # Set error code so we can handle it below.
                            s_json = {'code': 429, 'msg': 'Too Many Requests'}
                            break

                        if self.force_retry:
                            self.logger.error(f'REST {e}. {retries_remaining}')
                            await asyncio.sleep(self.retry_delay)
                            continue
                        else:
                            raise FailedRequestError(
                                request=f'{method} {url}: {req_params}',
                                message='Conflict. Could not decode JSON.',
                                status_code=409,
                                time = time.strftime("%H:%M:%S", time.gmtime())
                            )

            # If requests fires an error, retry. ClientOSError is derived from OSError and
            # ClientConnectionError. It engulfs ClientConnectorError. ServerConnectionError
            # is derived from ClientConnectionError, not ClientOSError in < 3.9.2 docs hierarchy.
            except(
                # Connection reset by peer - will retry request if force_retry=True
                aiohttp.client_exceptions.ClientOSError,
                # Timeout on reading data from socket - will retry request if force_retry=True
                aiohttp.client_exceptions.ServerTimeoutError
            ) as e:

                if self.force_retry:
                    self.logger.error(f'REST {e}. {retries_remaining}')
                    await asyncio.sleep(self.retry_delay)
                    req_params.pop('signature', None)
                    continue
                else:
                    raise e
        
            # Return response if no error.
            if s_json['code'] == 0:
                return s_json

            # Bingx returned an error, so handle and/or raise.

            # Generate error message.
            error_msg = (f'REST {s_json["msg"]} (HTTPStatus: {s.status}) (ErrCode: {s_json["code"]})')

            # Retry non-fatal whitelisted error requests.
            if s_json['code'] in self.retry_codes:

                # Set default retry delay.
                err_delay = self.retry_delay

                # 429, request too frequent; wait retry-after seconds and retry.
                if s_json['code'] in {429, 40029, 100410}:

                    self.logger.error(
                        f'{error_msg}. Ratelimited on current request. '
                        f'Sleeping, then trying again. Request: {url}'
                    )

                    # Calculate how long we need to wait. Get delay from headers.
                    if 'retry-after' in s.headers:
                        err_delay = int(s.headers['retry-after'])
                    elif 'X-RateLimit-Requests-Expire' in s.headers:
                        err_delay = int(s.headers['X-RateLimit-Requests-Expire']) / 1000
                    else:
                        err_delay = 5
                    limit_reset = time.time() + err_delay
                    reset_str = time.strftime(
                        "%X", time.localtime(limit_reset)
                    )

                    error_msg =(
                        f'Ratelimit will reset at {reset_str}. '
                        f'Sleeping for {err_delay} seconds'
                    )

                # Log the error.
                self.logger.error(f'{error_msg}. {retries_remaining}')
                await asyncio.sleep(err_delay)
                continue

            # Ignore whitelisted error requests.
            elif s_json['code'] in self.ignore_codes:
                pass

            # Raise for invalid authorization errors.
            elif s_json['code'] in {100001, 100004, 100413}:
                raise PermissionError(
                    f'Authorization failed. Please check your API keys and restart. '
                    f'Error: {error_msg}.'
                )

            else:
                raise InvalidRequestError(
                    request=f'{method} {url}: {req_params}',
                    message=s_json["msg"],
                    status_code=s_json["code"],
                    time=time.strftime("%H:%M:%S", time.gmtime())
                )


class WebSocket:
    """
    Connector for Bingx's WebSocket API.

    :param obj session: Required parameter. An aiohttp ClientSession constructed
        session instance.
    :param obj logger: Required parameter. An initialised logging object.
    :param str endpoint: Required parameter. The endpoint of the remote
        websocket.
    :param str api_key: Your API key. Required for authenticated endpoints.
        Defaults to None.
    :param list subscriptions: A list of desired topics to subscribe to. See
        Bingx API documentation for more information. Defaults to None.
    :param str logging_level: The logging level of the built-in logger. Defaults
        to logging.INFO. Options are CRITICAL (50), ERROR (40), WARNING (30),
        INFO (20), DEBUG (10), or NOTSET (0).
    :param int ping_interval: The number of seconds between each automated
        heartbeat Ping. The timer is reset on any data reception. Pong timeout
        is based on ping_interval/2
    :param bool restart_on_error: Whether or not the connection should restart
        on error.
    :param func error_cb_func: Callback function to bind to exception error
        handling.
    :param func account_cb_func: Callback function to bind to authenticated
        account data subscription events.

    :returns: WebSocket session.
    """

    def __init__(self, session, logger, endpoint, *, api_key=None, api_secret=None,
                 subscriptions=None, logging_level='INFO', ping_interval=20,
                 restart_on_error=True, error_cb_func=None, account_cb_func=None,
                 force_retry=False, max_retries=3, retry_delay=2):

        """
        Initializes the websocket session.
        """

        # Set websocket name for logging purposes
        self.wsName = 'Authenticated' if api_key else 'Non-Authenticated'

        # Setup logger.
        self.logger = logger
        self.logger.info(f'Initializing pyngx {self.wsName} WebSocket.')
    
        self.log_requests = False

        # Set aiohttp client session.
        self.session = session

        # Set endpoint.
        self.endpoint = endpoint

        # Set Listen Key endpoint.
        self.listen_key_endpoint = WS_LISTEN_KEY_URL

        # Set API keys.
        self.api_key = api_key

        # Set timeout to ClientTimeout sentinel.
        self.timeout = aiohttp.ClientTimeout(sock_read=10)
        self.force_retry = force_retry
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Set default aiohttp headers.
        self.headers = {
            'User-Agent': 'pyngx',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Initialize subscriptions set.
        self.subscriptions = set()

        # Set topic subscriptions for WebSocket.
        if subscriptions:
            self.subscriptions.update(subscriptions)

        # Set heartbeat ping interval
        self.ping_interval = ping_interval

        # Other optional data handling settings.
        self.handle_error = restart_on_error

        # Initialize handlers dictionary.
        self.handlers = {}

        # Bind account data callback function.
        if self.api_key:
            self.bind('account_data', account_cb_func)

        # Bind error handler callback function
        if error_cb_func:
            self.bind('error_cb', error_cb_func)

        # Set initial state and initialize dictionary.
        self._reset()

    def _reset(self):
        """
        Set state booleans and initialize dictionary.
        """

        self.exited = False
        self.ws = None
        self.listen_key = None
        self.logged_in = False
        self.connected = False
        self._subscribed = set()

    async def subscribe(self, subscriptions):
        """
        Subscribe to websocket topics.

        :param list subscriptions: Subscriptions in required
            format: ['<symbol>@depth<level>', ....]
        """

        # Update subscriptions set of topics.
        self.subscriptions.update(subscriptions)

        # Wait for connection to be opened/auth before subscribing.
        if not self.connected:
            self.logger.info(f'Waiting for WebSocket {self.wsName} to connect.')
            return

        # Generate list of current, non subscribed topics.
        topics = list(self.subscriptions - self._subscribed)

        if not topics:
            self.logger.info(f'Subscribe {subscriptions}, nothing to do!')
            return

        # Generate subscription args as list of dicts.
        self.logger.info(f"Subscribing to {topics}.")

        # Subscribe to the requested topics.
        await asyncio.gather(*[
            self.ws.send_json({'id': 'sub/' + t, 'reqType': 'sub', 'dataType': t})
            for t in topics
        ])

    async def unsubscribe(self, subscriptions):
        """
        Unsubscribe from websocket topics.

        :param list subscriptions: Subscriptions in required
            format: ['<symbol>@depth<level>', ....]
        """

        # Discard subscriptions from set
        self.subscriptions -= set(subscriptions)

        # Generate intersection list from current, subscribed topics.
        topics = [s for s in subscriptions if s in self._subscribed]

        if not topics:
            self.logger.info(f'Unsubscribe {subscriptions}, nothing to do!')
            return

        # Generate Unsubscribe args as list of dicts.
        self.logger.info(f"Unsubscribing from {topics}.")

        # Unsubscribe from the requested topics.
        await asyncio.gather(*[
            self.ws.send_json({'id': 'unsub/' + t, 'reqType': 'sub', 'dataType': t})
            for t in topics
        ])

    async def _connect(self):
        """
        Open websocket in a thread.
        """

        endpoint = self.endpoint

        # If given an api_key, authenticate and update endpoint.
        if self.api_key:
            await self._auth()
            endpoint = f'{self.endpoint}?listenKey={self.listen_key}'

        # Attempt to connect for X seconds.
        retries = 10
        while retries > 0:

            # Connect to WebSocket.
            try:
                self.ws = await self.session.ws_connect(
                    endpoint,
                    autoping=False,
                    heartbeat=self.ping_interval
                )

            # Handle errors during connection phase.
            except(
                aiohttp.client_exceptions.WSServerHandshakeError,
                aiohttp.client_exceptions.ClientOSError
            ) as e:
                self.logger.error(f'WebSocket connection {e!r}')
                retries -= 1

                # If connection was not successful, raise error.
                if retries <= 0:
                    raise WebSocketException(
                        f'{self.endpoint} Bad Request. Retries exceeded maximum. {e}'
                    )

            else:
                break

            await asyncio.sleep(1)

    async def _auth(self):
        """
        Authorize websocket connection.
        """

        # Get listenKey for authenticating.
        self.logger.info('Generating login authentication.')
        while not self.listen_key:
            await self._listen_key_generate()

    async def _listen_key_generate(self):
        resp, _ = await self._submit_request('POST')
        self.listen_key = resp['listenKey']

    async def _listen_key_extend(self):
        """
        Extend listen key validity period every 30 mins.
        """

        while True:
            await asyncio.sleep(1800)
            _, status = await self._submit_request('PUT')

            # Reset connection if listen key failure.
            if status != 200:
                raise WebSocketException(f'Websocket listen key extend failed with status: {status}.')

        self.logger.warning('Listen key extend has exited')

    async def _listen_key_delete(self):
        _, status = await self._submit_request('DELETE')

        # Reset connection if listen key failure.
        if status != 200:
            await self._reset()

    async def _submit_request(self, method=None):
        """
        Submits the listen key request to the API.
        """

        # Set listen key  url
        url = self.listen_key_endpoint

        # Set default request headers.
        r = {'headers': self.headers}

        # Prepare request.
        if method == 'POST':
            # Set additional header.
            r['headers']['X-BX-APIKEY'] = self.api_key

        elif method in {'PUT', 'DELETE'}:
            # Define query parameters.
            r['params'] = {'listenKey': self.listen_key}

        # Send request and return headers with body. Retry if failed.
        retries_attempted = self.max_retries

        while True:

            retries_attempted -= 1
            if retries_attempted < 0:
                raise FailedRequestError(
                    request=f'{method} {url}: {req_params}',
                    message='Bad Request. Retries exceeded maximum.',
                    status_code=400,
                    time = time.strftime("%H:%M:%S", time.gmtime())
                )

            retries_remaining = f'{retries_attempted} retries remain.'

            # Log the request.
            if self.log_requests:
                self.logger.info(f'Request -> {method} {url}: {r.get("params")}')

            # Attempt the request.
            try:
                async with self.session.request(
                    method, url, **r, timeout=self.timeout
                ) as s:

                    # Convert response to dictionary, or raise if requests error.
                    try:
                        s_json = await s.json()

                    # If we have trouble converting, handle the error and retry.
                    except aiohttp.client_exceptions.ContentTypeError as e:
                        if self.force_retry:
                            self.logger.error(f'{self.wsName} WebSocket {e}. {retries_remaining}')
                            await asyncio.sleep(self.retry_delay)
                            continue
                        else:
                            raise FailedRequestError(
                                request=f'{method} {url}: {req_params}',
                                message='Conflict. Could not decode JSON.',
                                status_code=409,
                                time = time.strftime("%H:%M:%S", time.gmtime())
                            )

            # If aiohttp fires an error, retry.
            except aiohttp.client_exceptions.ClientOSError as e:
                if self.force_retry:
                    self.logger.error(f'{self.wsName} WebSocket {e}. {retries_remaining}')
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    raise e

            # Return response and http status code.
            return s_json, s.status

    async def _dispatch(self):

        while True:
            msg = await self.ws.receive()

            if msg.type == aiohttp.WSMsgType.BINARY:

                # Perpetual: check 'Ping' in raw byte encoded gzip packet before
                # needing decompress. eg: gzip.compress(b'Ping', 2, mtime=0)
                if msg.data == b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff\n\xc8\xccK\x07\x04\x00\x00\xff\xff\xc3\x92\xe7\x85\x04\x00\x00\x00':
                    await self._on_ping()
                    continue

                # Decompress binary data to string. gzip = 16+zlib.MAX_WBITS = 31.
                data = zlib.decompress(msg.data, 31).decode()

                # Convert message to json and consume.
                try:
                    await self._consume(json.loads(data))

                except json.decoder.JSONDecodeError as e:
                    raise e

            elif msg.type == aiohttp.WSMsgType.ERROR:
                raise WebSocketException(f'WebSocket connection error. Code: {self.ws.close_code}; {msg}')

            # Handle EofStream (type 257, etc)
            elif msg.type in (
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.CLOSING,
                aiohttp.WSMsgType.CLOSED
            ):
                raise WebSocketException(f'WebSocket connection closed. Code: {self.ws.close_code}; {msg}')
    
            else:
                self.logger.info(f'dispatch received {msg.type} {msg}')

    async def _consume(self, msg: dict):
        """
        Consumer to parse and emit incoming messages.
        """

        # Market and subscription topics
        if 'dataType' in msg:

            if msg['code'] == 0:

                if msg['dataType']:
                    await self._emit(msg['dataType'], msg)

                # Subscription events
                elif 'id' in msg:
                    action, topic = msg['id'].split('/')

                    if action == 'sub':
                        self._on_subscribe(topic)
                    else:
                        self._on_unsubscribe(topic)

            # dataType (topic) not supported
            elif msg['code'] == 80015:
                raise WebSocketException(
                    f'Couldn\'t subscribe to topic. Error: {msg["msg"]} (ErrCode: {msg["code"]}).'
                )

            else:
                raise WebSocketException(f'Error: {msg["msg"]} (ErrCode: {msg["code"]}).')

        # Account Data (authenticated) events
        elif 'e' in msg:    # else

            # Bingx does not provide a login success or failure event
            # so use snapshot event to verify.
            if not self.logged_in and msg['e'] == 'SNAPSHOT':
                self._on_login()

            elif msg['e'] == 'listenKeyExpired':
                raise WebSocketException('Websocket listen key expired.')

            await self._emit('account_data', msg)

        return

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

    async def _on_open(self):
        """
        Perform tasks on WS open.
        """

        self.logger.info(f'WebSocket {self.wsName} opened.')

        # If given an api_key, wait for authentication success.
        if self.api_key and not self.logged_in:
            self.logger.info('Waiting for login authentication.')
            while not self.logged_in:
                await asyncio.sleep(0.01)

        # Connection is open.
        self.connected = True

        # Subscribe to websocket topics.
        if self.subscriptions:
            await self.subscribe(self.subscriptions)

    def _on_login(self):
        self.logged_in = True
        self.logger.info('Authentication successful.')

    def _on_subscribe(self, topic):
        """
        Log and store WS subscription successes.
        """

        self.logger.info(f'Subscription to {topic} successful.')
        self._subscribed.add(topic)

    def _on_unsubscribe(self, topic):
        """
        Log and remove WS unsubscribe successes.
        """

        self.logger.info(f'Unsubscribe from {topic} successful.')
        self._subscribed.discard(topic)

    @property
    def subscribed(self):
        return self._subscribed

    async def _on_ping(self):
        await self.ws.pong()

    async def _on_close(self):
        """
        Perform tasks on WS close.
        """

        self.logger.info(f'WebSocket {self.wsName} closed.')
        await self.exit()

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

    async def exit(self):
        """
        Closes the websocket connection.
        """

        if self.ws:
            await self.ws.close()
        self._reset()
        self.exited = True

    async def run_forever(self):

        self.logger.debug(f'WebSocket {self.wsName} starting stream.')

        while not self.exited:

            try:
                if not self.ws:
                    await self._connect()

                # Launch dispatch as background task to process packets.
                tasks = [asyncio.create_task(self._dispatch())]

                # Open topics, dispatch and listen key loops to keep connection alive.
                if self.api_key:
                    tasks.append(asyncio.create_task(self._listen_key_extend()))

                await asyncio.gather(*tasks, self._on_open())

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

            # Give event loop a foothold to juggle between coroutines
            await asyncio.sleep(0.01)


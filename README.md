# pyngx
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-2-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

[![Build Status](https://img.shields.io/pypi/pyversions/pyngx)](https://www.python.org/downloads/)
[![Build Status](https://img.shields.io/pypi/v/pyngx)](https://pypi.org/project/pyngx/)
[![Build Status](https://travis-ci.org/apf20/pyngx.svg?branch=master)](https://travis-ci.org/apf20/pyngx)
![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)

Python3 Asyncronous, Rate-Limit Aware, API connector for BingX's HTTP and Websockets APIs.

## Table of Contents

- [About](#about)
- [Development](#development)
- [Installation](#installation)
- [Usage](#usage)
- [Contact](#contact)
- [Contributors](#contributors)
- [Donations](#donations)

## About
Put simply, `pyngx` (Python + BingX) is a lightweight, fast, asyncronous, `rate-limit aware`
one-stop-shop module for the BingX REST HTTP and WebSocket APIs. It is built using built
in `asyncio` library and the `aiohttp` library.

I was never a fan of connectors that used a mosh-pit of various modules that you didn't
want, used up valuable resources and slowed down the connector, particularly with
syncronous code. So I decided to build my own Python3-dedicated connector with very
little external resources (`pyngx` uses only `aiohttp` package). The goal of the
connector is to provide traders and developers with an easy-to-use, lightning fast
asyncronous API connector module.

## Development
`pyngx` was a private module as part of proprietary trading strategies, it was being
actively developed, especially since BingX was making changes and improvements to
their API on a regular basis. It is compatible up to V2/3 of the BingX APIs. It has
now been open-sourced and is offered as a public, true `community` project. 

`pyngx` uses aiohttp for its methods, alongside other built-in modules, such as asyncio,
for high performance asyncronous operations.

`pyngx` is built with `rate-limit aware` methods, with REST API call maximum simultaneous
and time limits applied according to BingX documented endpoint limits.

Feel free to fork this repository, issue reports for any bugs and add pull requests for any
improvements and updates to BingX API changes.

## Installation
`pyngx` requires Python 3.8 or higher. The module can be installed manually. Pip
installation support will be considered.

## Usage
You can retrieve the HTTP and WebSocket classes like so:
```python
import asyncio
from pyngx import Exchange
```
Create an HTTP session and connect via WebSocket using context manager protocol:
```python
async def main():
    async with Exchange() as session:
        rest = session.rest(
            endpoint='https://open-api.bingx.com',
            api_key=...,
            api_secret=...,
            contract_type='usd_futures',
            force_retry=True
        )
        ws = session.websocket(
            endpoint='wss://open-api-swap.bingx.com/swap-market',
            subscriptions=['SOL-USDT@kline_1m']
        )
asyncio.run(main())
```
Information can be sent to, or retrieved from, the BingX APIs:
```python
async def main():
    async with Exchange() as session:
        rest = session.rest(...)

        # Get symbol ticker.
        await rest.do('get_quote_ticker', symbol='BTC-USDT')

        # Create five long orders.
        orders = [{
            'symbol': 'BTC-USDT',
            'type': 'LIMIT',
            'side': 'BUY',
            'positionSide': 'LONG',
            'price': i,
            'quantity': 0.1
        } for i in ['5000', '5500', '6000', '6500', '7000']]

        # Submit the orders in bulk, asyncronously.
        await self.rest.do('batch_create_order', orders = orders)

asyncio.run(main())
```
Check out the example python files, in the examples directory, for
more information, documentation and examples on available endpoints
and methods for the `HTTP` and `WebSocket` classes.

## Contact
I'm pretty responsive here on [Github](https://github.com).

## Contributors

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
      <td align="center"><a href="https://github.com/APF20"><img src="https://avatars0.githubusercontent.com/u/74583612?v=4" width="100px;" alt=""/><br /><sub><b>APF20</b></sub></a><br /><a href="https://github.com/APF20/pyngx/commits?author=APF20" title="Code">💻</a>  <a href="https://github.com/APF20/pyngx/commits?author=APF20" title="Documentation">📖</a></td>
  </tr>
</table>

<!-- markdownlint-enable -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) 
specification. Contributions of any kind welcome!

## Donations

I work on `pyngx` in my spare time. If you like the project and want to donate, 
you can do so to the following addresses:

```
SOL: HoUMsBKUESB9fsVTNtT4jYGnAzTAH9LNpZHjXvPiZ5Tb
BTC: bc1q4y230tg3rrhty9zxwpm63g5sgaqxw83xuwahjk
ETH: 0x06fd9aad799c5f094ce8c941fae9b81967cd8323
```

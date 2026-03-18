"""
asyncio time based rate limiter.

:copyright: (c) 2024 APF20

:license: MIT License
"""

import asyncio
from collections import deque

class RateLimiter:
    def __init__(self, max_calls, time_window):
        self.max_calls = max_calls
        self.time_window = time_window
        self.semaphore = asyncio.BoundedSemaphore(max_calls)
        self.timestamps = deque()

    async def _wait_for_token(self):
        while len(self.timestamps) >= self.max_calls:
            earliest_timestamp = self.timestamps[0]
            elapsed_time = asyncio.get_event_loop().time() - earliest_timestamp
            if elapsed_time < self.time_window:
                await asyncio.sleep(self.time_window - elapsed_time)
            else:
                self.timestamps.popleft()
        timestamp = asyncio.get_event_loop().time()
        self.timestamps.append(timestamp)

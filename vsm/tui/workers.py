"""Async workers for blocking operations in VSM TUI."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar

T = TypeVar("T")

# Shared executor for blocking operations
_executor = ThreadPoolExecutor(max_workers=4)


async def run_blocking(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a blocking function in a thread pool executor."""
    loop = asyncio.get_event_loop()
    if kwargs:
        return await loop.run_in_executor(
            _executor, lambda: func(*args, **kwargs)
        )
    return await loop.run_in_executor(_executor, func, *args)

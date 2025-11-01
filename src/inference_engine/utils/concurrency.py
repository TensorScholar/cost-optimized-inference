import asyncio
from typing import Iterable, Awaitable, TypeVar, List

T = TypeVar("T")


async def gather_limited(coros: Iterable[Awaitable[T]], limit: int = 10) -> List[T]:
    semaphore = asyncio.Semaphore(limit)
    results: List[T] = []

    async def _wrap(coro: Awaitable[T]) -> None:
        async with semaphore:
            res = await coro
            results.append(res)

    await asyncio.gather(*[_wrap(c) for c in coros])
    return results

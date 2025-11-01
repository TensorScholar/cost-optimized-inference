import asyncio
from ...config import settings


async def run_batch_processor() -> None:
    while True:
        # Placeholder: pull from queue and process
        await asyncio.sleep(1.0)

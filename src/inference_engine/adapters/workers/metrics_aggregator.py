import asyncio


async def run_metrics_aggregator() -> None:
    while True:
        # Placeholder: flush metrics to DB or logs
        await asyncio.sleep(10.0)

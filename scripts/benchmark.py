"""Benchmark script for performance testing."""
import asyncio
import time
import argparse
from typing import List

import httpx


async def run_benchmark(url: str, num_requests: int, concurrency: int):
    """Run benchmark against inference API."""
    print(f"Benchmark: {num_requests} requests, {concurrency} concurrent")
    
    async def make_request(client: httpx.AsyncClient):
        payload = {"prompt": "Tell me a joke", "max_tokens": 50}
        return await client.post(f"{url}/v1/inference", json=payload)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        start = time.time()
        
        tasks = []
        for _ in range(num_requests):
            tasks.append(make_request(client))
        
        # Run with limited concurrency
        results = []
        for i in range(0, len(tasks), concurrency):
            batch = tasks[i:i+concurrency]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)
        
        elapsed = time.time() - start
        
        # Analyze results
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = num_requests - successes
        
        print(f"\nResults:")
        print(f"  Requests: {num_requests}")
        print(f"  Successes: {successes}")
        print(f"  Failures: {failures}")
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Requests/sec: {num_requests/elapsed:.2f}")
        print(f"  Avg latency: {elapsed*1000/num_requests:.2f}ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark inference API")
    parser.add_argument("--url", default="http://localhost:8000", help="API URL")
    parser.add_argument("--requests", type=int, default=100, help="Number of requests")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent requests")
    
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.url, args.requests, args.concurrency))


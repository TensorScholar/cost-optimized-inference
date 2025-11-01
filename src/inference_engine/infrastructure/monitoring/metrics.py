from prometheus_client import Counter, Histogram

REQUEST_COUNTER = Counter("inference_requests_total", "Total inference requests", ["route"]) 
LATENCY_HIST = Histogram("inference_latency_ms", "Inference latency (ms)", buckets=(5,10,20,50,100,200,500,1000))
CACHE_HITS = Counter("cache_hits_total", "Cache hits", ["source"]) 


def record_request(route: str) -> None:
    REQUEST_COUNTER.labels(route=route).inc()


def observe_latency_ms(latency_ms: int) -> None:
    LATENCY_HIST.observe(float(latency_ms))

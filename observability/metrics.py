from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

REQUEST_COUNT = Counter("smartfood_requests_total", "Total requests", ["endpoint", "status"])
LATENCY = Histogram("smartfood_latency_seconds", "Request latency", ["endpoint"])
CACHE_HITS = Counter("smartfood_cache_hits_total", "Redis cache hits")
FRAUD_DETECTED = Counter("smartfood_fraud_detected_total", "Fraud events detected")
LLM_CALLS = Counter("smartfood_llm_calls_total", "LLM API calls made", ["model_version"])
IMAGE_GEN_CALLS = Counter("smartfood_image_gen_total", "Image generation calls", ["source"])

class timer:
    """Context manager to measure latency."""
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.start = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *_):
        self.elapsed_ms = (time.time() - self.start) * 1000
        LATENCY.labels(self.endpoint).observe(time.time() - self.start)

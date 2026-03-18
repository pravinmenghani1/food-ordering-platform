import uuid, time, os, json
import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import Response
from kafka import KafkaProducer
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from schemas.request import PredictRequest, FraudRequest, FeedbackRequest, ImageGenRequest
from schemas.response import PredictResponse, FraudResponse, ImageResponse
from observability.metrics import REQUEST_COUNT, LATENCY, CACHE_HITS, FRAUD_DETECTED, LLM_CALLS, IMAGE_GEN_CALLS, timer

app = FastAPI(title="SmartFood AI Gateway", version="1.0.0")

# ── Config ────────────────────────────────────────────────────────────────────
PREPROCESSING_URL = os.getenv("PREPROCESSING_URL", "http://localhost:8001")
INFERENCE_URL     = os.getenv("INFERENCE_URL",     "http://localhost:8002")
FRAUD_URL         = os.getenv("FRAUD_URL",         "http://localhost:8003")
IMAGE_GEN_URL     = os.getenv("IMAGE_GEN_URL",     "http://localhost:8004")
KAFKA_BOOTSTRAP   = os.getenv("KAFKA_BOOTSTRAP",   "localhost:9092")
REDIS_URL         = os.getenv("REDIS_URL",         "redis://localhost:6379")

# ── Rate limit store (in-memory for demo) ─────────────────────────────────────
_rate_store: dict[str, list] = {}
RATE_LIMIT = 10  # requests per minute per user

# ── Kafka producer (lazy init) ────────────────────────────────────────────────
_producer = None

def _get_producer():
    global _producer
    if _producer is None:
        try:
            _producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode(),
                request_timeout_ms=5000,
            )
        except Exception as e:
            print(f"[Kafka] producer init failed: {e}")
    return _producer

# ── Redis client ──────────────────────────────────────────────────────────────
redis_client: aioredis.Redis = None

@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _check_rate_limit(user_id: str):
    now = time.time()
    window = _rate_store.setdefault(user_id, [])
    _rate_store[user_id] = [t for t in window if now - t < 60]
    if len(_rate_store[user_id]) >= RATE_LIMIT:
        raise HTTPException(429, f"Rate limit exceeded ({RATE_LIMIT} req/min)")
    _rate_store[user_id].append(now)

def _ab_version(user_id: str, override: str | None) -> str:
    """Route 50/50 between v1 and v2 based on user_id hash."""
    if override:
        return override
    return "v2" if hash(user_id) % 2 == 0 else "v1"

def _publish(topic: str, payload: dict):
    p = _get_producer()
    if p:
        try:
            p.send(topic, payload)
            p.flush(timeout=3)
        except Exception as e:
            print(f"[Kafka] publish failed: {e}")

# ── Middleware: inject trace_id ───────────────────────────────────────────────
@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    request.state.trace_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Trace-ID"] = request.state.trace_id
    return response

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, request: Request, v: str = Query(None)):
    _check_rate_limit(req.user_id)
    trace_id = request.state.trace_id
    model_version = _ab_version(req.user_id, v or req.model_version)

    with timer("/predict") as t:
        async with httpx.AsyncClient(timeout=10) as client:
            # Step 1: preprocess
            pre = await client.post(f"{PREPROCESSING_URL}/preprocess", json={"text": req.input})
            clean_input = pre.json()["text"]

            # Step 2: inference (with cache check inside inference service)
            inf = await client.post(f"{INFERENCE_URL}/infer", json={
                "text": clean_input,
                "user_id": req.user_id,
                "model_version": model_version,
                "trace_id": trace_id,
            })
            result = inf.json()

    # Publish event to Kafka
    _publish("food-requests", {
        "trace_id": trace_id,
        "user_id": req.user_id,
        "input": req.input,
        "prediction": result["prediction"],
        "model_version": model_version,
        "timestamp": time.time(),
    })

    REQUEST_COUNT.labels("/predict", "200").inc()
    LLM_CALLS.labels(model_version).inc()

    return PredictResponse(
        prediction=result["prediction"],
        confidence=result["confidence"],
        trace_id=trace_id,
        model_version=model_version,
        cached=result.get("cached", False),
        latency_ms=round(t.elapsed_ms, 2),
    )

@app.post("/fraud", response_model=FraudResponse)
async def fraud_check(req: FraudRequest, request: Request):
    trace_id = request.state.trace_id
    async with httpx.AsyncClient(timeout=5) as client:
        res = await client.post(f"{FRAUD_URL}/detect", json=req.dict())
    result = res.json()

    if result["is_fraud"]:
        FRAUD_DETECTED.inc()
        _publish("fraud-alerts", {**result, "trace_id": trace_id, "user_id": req.user_id})

    REQUEST_COUNT.labels("/fraud", "200").inc()
    return FraudResponse(**result, trace_id=trace_id)

@app.get("/image/legacy", response_model=ImageResponse)
async def legacy_image(item: str = Query(..., description="Food item name")):
    """
    📸 LEGACY: Returns a static, low-quality placeholder image.
    This is what the platform used before AI — blurry, unappealing photos
    that failed to attract customers.
    """
    IMAGE_GEN_CALLS.labels("legacy").inc()
    return ImageResponse(
        item_name=item,
        image_url=f"https://via.placeholder.com/400x300.png?text={item.replace(' ', '+')}",
        source="legacy",
    )

@app.post("/image/generate", response_model=ImageResponse)
async def generate_image(req: ImageGenRequest):
    """
    🤖 AI-POWERED: Generates a professional, appetizing food image using GenAI.
    This is the transformation — same food item, dramatically better visuals,
    leading to higher customer engagement and orders.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(f"{IMAGE_GEN_URL}/generate", json=req.dict())
    result = res.json()
    IMAGE_GEN_CALLS.labels("ai_generated").inc()
    return ImageResponse(**result)

@app.post("/feedback")
async def feedback(req: FeedbackRequest, request: Request):
    """Collect user feedback → feeds back into model improvement loop."""
    _publish("feedback-events", {
        **req.dict(),
        "timestamp": time.time(),
        "trace_id": request.state.trace_id,
    })
    return {"status": "feedback recorded", "trace_id": request.state.trace_id}

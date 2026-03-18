import os, hashlib, time
from fastapi import FastAPI
from pydantic import BaseModel
import redis
from openai import OpenAI

app = FastAPI(title="Inference Service")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "mock")
CACHE_TTL = 3600  # 1 hour

cache = redis.from_url(REDIS_URL, decode_responses=True)
llm = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY != "mock" else None

# ── Prompt versions (prompt versioning demo) ──────────────────────────────────
PROMPTS = {
    "v1": "You are a food assistant. Suggest 3 dishes for: {input}",
    "v2": (
        "You are SmartFood AI, an expert culinary assistant. "
        "Given the user's preference: '{input}', recommend 3 personalized dishes. "
        "For each dish include: name, cuisine type, and why it matches their taste. "
        "Be concise and appetizing."
    ),
}

# ── Mock responses when no API key ────────────────────────────────────────────
MOCK_RESPONSES = {
    "v1": lambda inp: f"Based on '{inp}': 1. Spicy Ramen 2. Pad Thai 3. Butter Chicken",
    "v2": lambda inp: (
        f"For your love of '{inp}', here are 3 perfect picks:\n"
        "1. 🍜 Spicy Tonkotsu Ramen (Japanese) — rich broth with a fiery kick\n"
        "2. 🍛 Chettinad Chicken Curry (Indian) — bold spices, aromatic\n"
        "3. 🌮 Birria Tacos (Mexican) — slow-cooked, deeply flavored"
    ),
}

class InferRequest(BaseModel):
    text: str
    user_id: str
    model_version: str = "v1"
    trace_id: str = ""

def _cache_key(text: str, version: str) -> str:
    return f"infer:{version}:{hashlib.md5(text.encode()).hexdigest()}"

def _call_llm(text: str, version: str) -> str:
    prompt = PROMPTS.get(version, PROMPTS["v1"]).format(input=text)
    if llm:
        resp = llm.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        return resp.choices[0].message.content
    return MOCK_RESPONSES.get(version, MOCK_RESPONSES["v1"])(text)

@app.post("/infer")
def infer(req: InferRequest):
    key = _cache_key(req.text, req.model_version)

    # Cache check
    cached = cache.get(key)
    if cached:
        return {"prediction": cached, "confidence": 0.95, "cached": True}

    start = time.time()
    prediction = _call_llm(req.text, req.model_version)
    latency = time.time() - start

    cache.setex(key, CACHE_TTL, prediction)

    return {
        "prediction": prediction,
        "confidence": round(0.75 + (0.2 * (req.model_version == "v2")), 2),
        "cached": False,
        "latency_ms": round(latency * 1000, 2),
    }

@app.get("/health")
def health():
    return {"status": "ok"}

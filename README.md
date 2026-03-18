# 🍔 SmartFood AI Platform

A production-grade, AI-first food ordering platform built for learning.
Demonstrates GenAI, microservices, event-driven architecture, and observability.

---

## 🧠 The Story

**Before AI:** Restaurants uploaded blurry phone photos of their food.
Customers scrolled past. Orders were low. Engagement was terrible.

**After AI:** The same restaurant types a description like *"Spicy Margherita Pizza, crispy crust, fresh basil"*
and GenAI generates a professional, mouth-watering food photograph instantly.
Click-through rates go up 3x. Orders increase. Restaurants are happy.

That's the transformation this platform demonstrates — and it's just the beginning.

---

## 🏗️ Architecture

```
                        ┌─────────────────────────────────────────┐
                        │           API GATEWAY :8000              │
                        │  • Rate Limiting  • Trace ID injection   │
                        │  • A/B Routing    • Prometheus metrics   │
                        └──────┬──────────┬──────────┬────────────┘
                               │          │          │
              ┌────────────────▼──┐  ┌────▼────┐  ┌─▼──────────────┐
              │ Preprocessing     │  │ Fraud   │  │ Image Gen      │
              │ Service :8001     │  │ Service │  │ Service :8004  │
              │ • Text cleaning   │  │ :8003   │  │ • Legacy mode  │
              │ • Tokenization    │  │ • Rules │  │ • DALL-E / AI  │
              └────────────────┬──┘  │ • Score │  └────────────────┘
                               │     └─────────┘
              ┌────────────────▼──────────────────┐
              │       Inference Service :8002      │
              │  • LLM calls (OpenAI / mock)       │
              │  • Prompt versioning (v1/v2)       │
              │  • Redis embedding cache           │
              │  • A/B model routing               │
              └────────────────┬──────────────────┘
                               │
              ┌────────────────▼──────────────────┐
              │            KAFKA                   │
              │  Topics: food-requests             │
              │          feedback-events           │
              │          fraud-alerts              │
              └────────────────┬──────────────────┘
                               │
              ┌────────────────▼──────────────────┐
              │       Feedback Consumer            │
              │  • Closes the AI feedback loop     │
              │  • Aggregates ratings              │
              │  • Triggers retraining signals     │
              └───────────────────────────────────┘

  Redis ──── Caching LLM responses (cost optimization)
  Prometheus ── Metrics scraping from all services
  Grafana ──── Dashboards (latency, errors, cache hits)
  Jaeger ───── Distributed tracing (Gateway → Service → Kafka)
```

---

## 🚀 Quick Start

```bash
# 1. Start everything
make up

# 2. Run smoke tests
make test

# 3. View logs
make logs

# 4. Tear down
make down
```

### With real OpenAI (optional)
```bash
export OPENAI_API_KEY=sk-...
make up
```
Without a key, the platform runs in **mock mode** — all features work with simulated responses.

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/predict` | POST | AI food recommendations (LLM) |
| `/fraud` | POST | Real-time fraud detection |
| `/image/legacy` | GET | Old platform: static placeholder image |
| `/image/generate` | POST | AI-generated professional food photo |
| `/feedback` | POST | Submit rating → feeds back to model |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/docs` | GET | Interactive Swagger UI |

---

## 🧪 Demo Walkthrough (for class)

### 1. The Image Transformation Story
```bash
# Legacy: blurry placeholder
curl "http://localhost:8000/image/legacy?item=pizza"

# AI-powered: professional food photography
curl -X POST http://localhost:8000/image/generate \
  -H "Content-Type: application/json" \
  -d '{"item_name": "Spicy Margherita Pizza", "description": "crispy crust, fresh basil, wood-fired"}'
```
Open both URLs in a browser. **That's the business impact of GenAI.**

### 2. AI Food Recommendations
```bash
# v1 prompt (basic)
curl -X POST "http://localhost:8000/predict?v=v1" \
  -H "Content-Type: application/json" \
  -d '{"input": "I love spicy food", "user_id": "student_1"}'

# v2 prompt (detailed, higher quality)
curl -X POST "http://localhost:8000/predict?v=v2" \
  -H "Content-Type: application/json" \
  -d '{"input": "I love spicy food", "user_id": "student_1"}'
```
Notice: v2 gives richer recommendations. **That's prompt versioning.**

### 3. Redis Cache in Action
```bash
# First call — hits LLM (cached: false)
curl -X POST "http://localhost:8000/predict?v=v1" \
  -d '{"input": "vegetarian options", "user_id": "u1"}' -H "Content-Type: application/json"

# Second call — instant (cached: true, latency ~1ms)
curl -X POST "http://localhost:8000/predict?v=v1" \
  -d '{"input": "vegetarian options", "user_id": "u1"}' -H "Content-Type: application/json"
```
**That's cost optimization** — same LLM result, zero API cost on repeat.

### 4. Fraud Detection
```bash
curl -X POST http://localhost:8000/fraud \
  -H "Content-Type: application/json" \
  -d '{"input": "free money hack bypass", "user_id": "bad_actor", "order_amount": 9999}'
```

### 5. Feedback Loop
```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"trace_id": "abc-123", "user_id": "u1", "rating": 5, "prediction": "Ramen", "was_helpful": true}'
```
Watch the feedback-consumer logs: `docker-compose logs -f feedback-consumer`

### 6. A/B Testing
```bash
# Different user_ids get routed to different model versions automatically
for i in 1 2 3 4 5; do
  curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"input\": \"pizza\", \"user_id\": \"user_$i\"}" | python3 -m json.tool | grep model_version
done
```

---

## 📊 Observability

| Tool | URL | Credentials |
|---|---|---|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| Jaeger | http://localhost:16686 | — |
| API Docs | http://localhost:8000/docs | — |

**Key metrics to show in Grafana:**
- `smartfood_requests_total` — request volume
- `smartfood_latency_seconds` — p50/p95 latency
- `smartfood_cache_hits_total` — cache efficiency
- `smartfood_fraud_detected_total` — fraud events
- `smartfood_llm_calls_total` — LLM usage by model version

---

## 🗂️ Project Structure

```
smartfood-ai-platform/
├── docker-compose.yml          # Orchestrates all services
├── Makefile                    # make up / down / test / logs
├── api-gateway/                # Entry point, routing, rate limiting, A/B
├── services/
│   ├── preprocessing-service/  # Text cleaning & normalization
│   ├── inference-service/      # LLM + Redis cache + prompt versioning
│   ├── fraud-service/          # Real-time fraud scoring
│   └── image-gen-service/      # Legacy vs AI image generation
├── event-system/
│   ├── producers/              # Kafka producers
│   └── consumers/              # Inference + feedback consumers
├── schemas/                    # Shared Pydantic models
└── observability/              # Prometheus + Grafana config
```

---

## 🔑 Key Concepts Demonstrated

| Concept | Where |
|---|---|
| GenAI image generation | `image-gen-service` |
| LLM food recommendations | `inference-service` |
| Prompt versioning (v1/v2) | `inference-service/app.py` → `PROMPTS` dict |
| A/B model routing | `api-gateway/main.py` → `_ab_version()` |
| Redis embedding cache | `inference-service/app.py` → cache check |
| Kafka event pipeline | `event-system/` |
| Fraud detection | `fraud-service/app.py` |
| Distributed tracing | `X-Trace-ID` header on every response |
| Rate limiting | `api-gateway/main.py` → `_check_rate_limit()` |
| Prometheus metrics | `/metrics` endpoint on gateway |
| Feedback loop | `feedback-consumer` → aggregates ratings |

---

## ⚖️ Trade-offs (Discussion Points)

| Decision | Trade-off |
|---|---|
| Sync API vs Kafka async | Latency vs throughput |
| Redis cache | Stale recommendations vs LLM cost |
| Mock mode vs real LLM | Works offline, but less impressive |
| Rule-based fraud vs ML | Fast & explainable vs accurate |
| Monolith vs microservices | Simplicity vs scalability |

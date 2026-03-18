# 🍔 SmartFood AI Platform — 12-Hour Lab Guide

> **Goal:** Build and understand a production-grade AI food ordering platform from scratch.
> Each phase has a time budget, clear commands, and things to observe.

---

## ⚙️ Prerequisites (Before You Start)

```bash
# Verify these are installed
docker --version        # Docker 24+
docker-compose --version
python3 --version       # 3.10+
curl --version
```

Optional (for real AI):
```bash
export OPENAI_API_KEY=sk-...   # skip to run in mock mode — everything still works
```

---

## ⏱️ PHASE 0 — Environment Setup (30 mins)

### Step 1 — Clone and enter the project
```bash
git clone <repo-url> smartfood-ai-platform
cd smartfood-ai-platform
```

### Step 2 — Understand the project layout
```
smartfood-ai-platform/
├── docker-compose.yml          ← orchestrates ALL services
├── Makefile                    ← make up / down / test / logs
├── api-gateway/                ← single entry point for all traffic
├── services/
│   ├── preprocessing-service/  ← cleans user input before LLM
│   ├── inference-service/      ← LLM calls + Redis cache + prompt versioning
│   ├── fraud-service/          ← real-time fraud scoring
│   └── image-gen-service/      ← legacy placeholder vs DALL-E AI images
├── event-system/
│   ├── producers/              ← publishes events to Kafka
│   └── consumers/              ← feedback loop + inference consumer
├── schemas/                    ← shared Pydantic request/response models
└── observability/              ← Prometheus + Grafana config
```

### Step 3 — Start the platform
```bash
make up
```

**Expected output:**
```
✅ SmartFood AI Platform is running!
  API Gateway:    http://localhost:8000/docs
  Grafana:        http://localhost:3000  (admin/admin)
  Prometheus:     http://localhost:9090
  Jaeger UI:      http://localhost:16686
```

### Step 4 — Verify all containers are healthy
```bash
docker-compose ps
```
You should see 10 containers: zookeeper, kafka, redis, jaeger, prometheus, grafana,
preprocessing-service, inference-service, fraud-service, image-gen-service, api-gateway, feedback-consumer.

### Step 5 — Open the interactive API docs
Open in browser: **http://localhost:8000/docs**

> 💡 FastAPI auto-generates this from your code. Every endpoint is testable here.

---

## ⏱️ PHASE 1 — Understand the API Gateway (45 mins)

The gateway is the single front door. All traffic enters here.

### Step 6 — Read the gateway code
Open `api-gateway/main.py` and find these 4 key concepts:

**A) Trace ID injection (every request gets a unique ID)**
```python
# middleware injects this on every request
request.state.trace_id = str(uuid.uuid4())
response.headers["X-Trace-ID"] = request.state.trace_id
```

**B) Rate limiting (per user, in-memory)**
```python
if len(_rate_store[user_id]) >= RATE_LIMIT:
    raise HTTPException(429, "Rate limit exceeded")
```

**C) A/B routing (50/50 split by user_id hash)**
```python
def _ab_version(user_id: str, override: str | None) -> str:
    return "v2" if hash(user_id) % 2 == 0 else "v1"
```

**D) Kafka publishing (fire-and-forget after response)**
```python
_publish("food-requests", { "trace_id": ..., "user_id": ..., ... })
```

### Step 7 — Make your first API call
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

### Step 8 — Check the trace ID in response headers
```bash
curl -si http://localhost:8000/health | grep X-Trace-ID
```
Every response carries a trace ID. This is how you correlate logs across services.

---

## ⏱️ PHASE 2 — The Image Transformation Story (45 mins)

> This is the core business narrative. Show this to students first.

### Step 9 — The BEFORE: Legacy platform
```bash
curl -s "http://localhost:8000/image/legacy?item=pizza" | python3 -m json.tool
```

**What you see:**
```json
{
  "item_name": "pizza",
  "image_url": "https://via.placeholder.com/400x300.png?text=pizza",
  "source": "legacy"
}
```
Open that URL in a browser. That's a grey placeholder. **Customers scroll past this.**

### Step 10 — The AFTER: AI-generated image
```bash
curl -s -X POST http://localhost:8000/image/generate \
  -H "Content-Type: application/json" \
  -d '{"item_name": "Spicy Margherita Pizza", "description": "crispy crust, fresh basil, wood-fired"}' \
  | python3 -m json.tool
```

**What you see:**
```json
{
  "item_name": "Spicy Margherita Pizza",
  "image_url": "https://...",
  "source": "ai_generated",
  "prompt_used": "Professional food photography of Spicy Margherita Pizza..."
}
```
Open that URL. **That's a professional food photo generated from text in seconds.**

### Step 11 — Read the image-gen service code
Open `services/image-gen-service/app.py`.

Key things to notice:
- `_build_prompt()` — crafts a detailed photography prompt from a simple item name
- `MOCK_AI_IMAGES` — curated Unsplash photos used when no API key is set
- The `source` field tells you whether it came from legacy or AI

> 💡 Discussion: The restaurant didn't change their food. They just described it better.
> GenAI did the rest. That's the business impact.

---

## ⏱️ PHASE 3 — LLM Recommendations + Prompt Versioning (60 mins)

### Step 12 — Basic food recommendation (v1 prompt)
```bash
curl -s -X POST "http://localhost:8000/predict?v=v1" \
  -H "Content-Type: application/json" \
  -d '{"input": "I love spicy food", "user_id": "student_1"}' \
  | python3 -m json.tool
```

### Step 13 — Better recommendation (v2 prompt)
```bash
curl -s -X POST "http://localhost:8000/predict?v=v2" \
  -H "Content-Type: application/json" \
  -d '{"input": "I love spicy food", "user_id": "student_1"}' \
  | python3 -m json.tool
```

**Compare the outputs.** v2 gives structured recommendations with cuisine type and reasoning.

### Step 14 — Read the prompt versions in code
Open `services/inference-service/app.py` and find the `PROMPTS` dict:

```python
PROMPTS = {
    "v1": "You are a food assistant. Suggest 3 dishes for: {input}",
    "v2": "You are SmartFood AI... recommend 3 personalized dishes. For each include: name, cuisine type, and why it matches their taste..."
}
```

> 💡 Discussion: Same model, different prompt = dramatically different output quality.
> This is why prompt versioning matters in production — you can A/B test prompts
> without changing any model code.

### Step 15 — Understand the full request flow
```
User → API Gateway → Preprocessing Service → Inference Service → Redis Cache → LLM
```

Trace it in the code:
1. `api-gateway/main.py` → `/predict` route calls preprocessing, then inference
2. `services/preprocessing-service/app.py` → lowercases, removes stop words
3. `services/inference-service/app.py` → checks Redis cache, calls LLM if miss

---

## ⏱️ PHASE 4 — Redis Caching (Cost Optimization) (45 mins)

### Step 16 — First call (cache miss)
```bash
curl -s -X POST "http://localhost:8000/predict?v=v1" \
  -H "Content-Type: application/json" \
  -d '{"input": "vegetarian options", "user_id": "u1"}' \
  | python3 -m json.tool
```
Note: `"cached": false` and latency ~1000-3000ms (LLM call).

### Step 17 — Second call (cache hit)
```bash
curl -s -X POST "http://localhost:8000/predict?v=v1" \
  -H "Content-Type: application/json" \
  -d '{"input": "vegetarian options", "user_id": "u1"}' \
  | python3 -m json.tool
```
Note: `"cached": true` and latency ~5ms. **Same result, zero LLM cost.**

### Step 18 — Inspect the cache key logic
Open `services/inference-service/app.py`:

```python
def _cache_key(text: str, version: str) -> str:
    return f"infer:{version}:{hashlib.md5(text.encode()).hexdigest()}"
```

The cache key is `version + MD5(cleaned_input)`. Same input + same version = same key = cache hit.

### Step 19 — Connect to Redis directly and inspect
```bash
docker exec -it food-ordering-platform-redis-1 redis-cli
> KEYS infer:*
> GET <one of the keys>
> TTL <one of the keys>
```

You'll see the cached LLM response stored as a string with a 3600s TTL.

> 💡 Discussion: In production, LLM calls cost money per token. Caching identical
> queries saves significant cost at scale. The trade-off: cached responses can go stale
> if the model or prompt changes.

---

## ⏱️ PHASE 5 — A/B Testing (30 mins)

### Step 20 — Watch A/B routing in action
```bash
for i in 1 2 3 4 5 6 7 8; do
  version=$(curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"input\": \"pizza\", \"user_id\": \"user_$i\"}" \
    | grep -o '"model_version":"[^"]*"' | cut -d'"' -f4)
  echo "user_$i → $version"
done
```

You'll see roughly half get v1, half get v2 — deterministically based on user_id.

### Step 21 — Understand the routing logic
```python
def _ab_version(user_id: str, override: str | None) -> str:
    return "v2" if hash(user_id) % 2 == 0 else "v1"
```

Same user always gets the same version (consistent experience).
Different users get different versions (experiment runs in parallel).

> 💡 Discussion: This is how companies like Netflix and Spotify test new AI models
> without disrupting all users. You measure quality metrics per group, then promote
> the winner.

---

## ⏱️ PHASE 6 — Fraud Detection (30 mins)

### Step 22 — Legitimate order
```bash
curl -s -X POST http://localhost:8000/fraud \
  -H "Content-Type: application/json" \
  -d '{"input": "2 pizzas and a coke", "user_id": "normal_user", "order_amount": 25}' \
  | python3 -m json.tool
```

### Step 23 — Fraudulent order
```bash
curl -s -X POST http://localhost:8000/fraud \
  -H "Content-Type: application/json" \
  -d '{"input": "free money hack bypass", "user_id": "bad_actor", "order_amount": 9999}' \
  | python3 -m json.tool
```

**Expected:**
```json
{
  "is_fraud": true,
  "fraud_score": 1.0,
  "reason": "keyword: 'hack'; keyword: 'free money'; unusually high order amount"
}
```

### Step 24 — Read the scoring logic
Open `services/fraud-service/app.py`. The `_score()` function:
- Checks for fraud keywords (+0.4 each)
- Checks for risky patterns (+0.2 each)
- Flags high order amounts (+0.3)
- Caps at 1.0, threshold at 0.5

> 💡 Discussion: Rule-based fraud is fast and explainable but brittle.
> ML-based fraud (trained on historical data) is more accurate but a black box.
> Production systems often use both in layers.

---

## ⏱️ PHASE 7 — Kafka Event Pipeline (60 mins)

### Step 25 — Watch events flow through Kafka
Open a new terminal and tail the feedback consumer:
```bash
docker-compose logs -f feedback-consumer
```

### Step 26 — Trigger events by making API calls
In your original terminal:
```bash
# This triggers a food-requests Kafka event
curl -s -X POST "http://localhost:8000/predict?v=v1" \
  -H "Content-Type: application/json" \
  -d '{"input": "sushi", "user_id": "kafka_demo"}' > /dev/null

# This triggers a fraud-alerts Kafka event
curl -s -X POST http://localhost:8000/fraud \
  -H "Content-Type: application/json" \
  -d '{"input": "free money hack", "user_id": "bad_actor", "order_amount": 9999}' > /dev/null
```

Watch the consumer terminal — you'll see the events arrive.

### Step 27 — Submit feedback (closes the loop)
```bash
curl -s -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"trace_id": "abc-123", "user_id": "u1", "rating": 5, "prediction": "Spicy Ramen", "was_helpful": true}' \
  | python3 -m json.tool
```

Watch the consumer log show: `[FEEDBACK] user=u1 rating=5/5 avg_rating=5.00 helpful=True`

### Step 28 — Understand the Kafka topics
```bash
docker exec food-ordering-platform-kafka-1 \
  kafka-topics --bootstrap-server localhost:9092 --list
```

Three topics:
- `food-requests` — every prediction request
- `feedback-events` — user ratings
- `fraud-alerts` — detected fraud

> 💡 Discussion: Why Kafka instead of direct DB writes?
> - Decouples producers from consumers (inference service doesn't know about analytics)
> - Handles traffic spikes (Kafka buffers, consumers process at their own pace)
> - Enables multiple consumers (analytics, retraining, alerting) from one event stream

---

## ⏱️ PHASE 8 — Observability (45 mins)

### Step 29 — Generate some traffic first
```bash
for i in $(seq 1 20); do
  curl -s -X POST "http://localhost:8000/predict?v=v$((RANDOM % 2 + 1))" \
    -H "Content-Type: application/json" \
    -d "{\"input\": \"food $i\", \"user_id\": \"load_user_$i\"}" > /dev/null
done
echo "Done generating traffic"
```

### Step 30 — View raw Prometheus metrics
```bash
curl -s http://localhost:8000/metrics | grep smartfood
```

You'll see counters like:
```
smartfood_requests_total{endpoint="/predict",status="200"} 20.0
smartfood_llm_calls_total{model_version="v1"} 10.0
smartfood_llm_calls_total{model_version="v2"} 10.0
smartfood_cache_hits_total 5.0
```

### Step 31 — Open Prometheus UI
Go to **http://localhost:9090**

Try these queries:
```
# Total requests
smartfood_requests_total

# Request rate (per second over last 5 min)
rate(smartfood_requests_total[5m])

# p95 latency
histogram_quantile(0.95, rate(smartfood_latency_seconds_bucket[5m]))

# Cache hit rate
rate(smartfood_cache_hits_total[5m])
```

### Step 32 — Open Grafana
Go to **http://localhost:3000** (admin / admin)

1. Click "Explore" in the left sidebar
2. Select "Prometheus" as data source
3. Run the same queries from Step 31
4. Click the graph icon to visualize

> 💡 Discussion: In production, you'd have pre-built dashboards with alerts.
> When p95 latency spikes, you get paged. When fraud rate jumps, security is notified.
> Observability is what separates a demo from a production system.

### Step 33 — Open Jaeger (distributed tracing)
Go to **http://localhost:16686**

> The X-Trace-ID header on every response is the foundation for distributed tracing.
> In a full Jaeger integration, you'd see the entire request journey:
> Gateway → Preprocessing → Inference → Redis → LLM → Kafka

---

## ⏱️ PHASE 9 — Rate Limiting (15 mins)

### Step 34 — Hit the rate limit
```bash
for i in $(seq 1 12); do
  echo -n "Request $i: "
  curl -s -X POST "http://localhost:8000/predict?v=v1" \
    -H "Content-Type: application/json" \
    -d '{"input": "pizza", "user_id": "rate_test_user"}' \
    | grep -o '"detail":"[^"]*"\|"model_version":"[^"]*"' | head -1 | cut -d'"' -f4
done
```

After 10 requests from the same user within a minute, you'll see:
```
Request 11: Rate limit exceeded (10 req/min)
```

> 💡 Discussion: Rate limiting protects your LLM budget. Without it, one user
> could exhaust your entire OpenAI quota in seconds.

---

## ⏱️ PHASE 10 — System Design Discussion (60 mins)

### Step 35 — Draw the architecture
Use the diagram from README.md as a base. Walk through each component:

```
User Request
    ↓
API Gateway (rate limit, trace ID, A/B routing)
    ↓
Preprocessing Service (clean text)
    ↓
Inference Service (check Redis cache → LLM if miss → cache result)
    ↓
Response to user
    ↓ (async, fire-and-forget)
Kafka → feedback-consumer (aggregates ratings, triggers retraining signals)
```

### Step 36 — Trade-off discussion table

| Decision | What we chose | Trade-off |
|---|---|---|
| Sync API vs async Kafka | Both — sync for response, async for events | User gets fast response; analytics happen in background |
| Redis cache | Cache LLM responses for 1 hour | Saves cost; risk of stale recommendations |
| Rule-based fraud | Keyword + amount scoring | Fast & explainable; misses novel fraud patterns |
| Mock mode | Works without API key | Great for demos; less impressive than real AI |
| Microservices | 4 separate services | Independent scaling; more operational complexity |
| Prompt versioning | v1/v2 in a dict | Easy to add versions; no DB needed for demo |

### Step 37 — Scaling discussion

**What breaks first at 10x traffic?**
- Inference service (LLM calls are slow and expensive)
- Redis (single node, no replication)
- Kafka (single broker, no partitioning)

**How would you fix each?**
- Inference: horizontal scaling + smarter cache (semantic similarity, not exact match)
- Redis: Redis Cluster or read replicas
- Kafka: add partitions, add brokers, consumer groups

---

## ⏱️ PHASE 11 — Full End-to-End Demo Flow (30 mins)

Run this as the final classroom demo. Each command tells a story.

### The Complete Story in 6 Commands

```bash
# 1. THE PROBLEM: blurry legacy image
echo "=== BEFORE AI: Legacy Image ==="
curl -s "http://localhost:8000/image/legacy?item=Margherita+Pizza" | python3 -m json.tool

# 2. THE SOLUTION: AI-generated professional photo
echo "=== AFTER AI: Generated Image ==="
curl -s -X POST http://localhost:8000/image/generate \
  -H "Content-Type: application/json" \
  -d '{"item_name": "Margherita Pizza", "description": "crispy crust, fresh basil, wood-fired"}' \
  | python3 -m json.tool

# 3. SMART RECOMMENDATIONS: LLM-powered
echo "=== AI Recommendation (v2 prompt) ==="
curl -s -X POST "http://localhost:8000/predict?v=v2" \
  -H "Content-Type: application/json" \
  -d '{"input": "I love spicy vegetarian food", "user_id": "demo_user"}' \
  | python3 -m json.tool

# 4. CACHE HIT: repeat the same query
echo "=== Same Query Again (should be cached) ==="
curl -s -X POST "http://localhost:8000/predict?v=v2" \
  -H "Content-Type: application/json" \
  -d '{"input": "I love spicy vegetarian food", "user_id": "demo_user"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'cached={d[\"cached\"]} latency={d[\"latency_ms\"]}ms')"

# 5. FRAUD DETECTION: catch bad actors
echo "=== Fraud Detection ==="
curl -s -X POST http://localhost:8000/fraud \
  -H "Content-Type: application/json" \
  -d '{"input": "free money hack bypass", "user_id": "bad_actor", "order_amount": 9999}' \
  | python3 -m json.tool

# 6. FEEDBACK LOOP: user rates the recommendation
echo "=== Feedback Loop ==="
curl -s -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"trace_id": "demo-123", "user_id": "demo_user", "rating": 5, "prediction": "Spicy Paneer Tikka", "was_helpful": true}' \
  | python3 -m json.tool
```

---

## ⏱️ PHASE 12 — Teardown + Recap (15 mins)

### Step 38 — Stop everything
```bash
make down
```

### Step 39 — What you built today

| Component | Technology | Concept |
|---|---|---|
| API Gateway | FastAPI | Single entry point, middleware, routing |
| Preprocessing | FastAPI | Text normalization pipeline |
| Inference | FastAPI + OpenAI | LLM integration, prompt versioning |
| Fraud Detection | FastAPI | Rule-based scoring |
| Image Generation | FastAPI + DALL-E | GenAI, legacy vs AI comparison |
| Caching | Redis | Cost optimization, TTL-based invalidation |
| Event Pipeline | Kafka | Async processing, decoupled architecture |
| Feedback Loop | Kafka Consumer | Closing the AI improvement cycle |
| Metrics | Prometheus | Counters, histograms, scraping |
| Dashboards | Grafana | Visualization, alerting foundation |
| Tracing | Jaeger + X-Trace-ID | Request correlation across services |
| Containerization | Docker Compose | Reproducible environments |

---

## 🔥 Bonus Challenges (if time permits)

**1. Add a new prompt version (v3)**
Edit `services/inference-service/app.py`, add to `PROMPTS` dict, rebuild:
```bash
docker-compose up --build -d inference-service
```

**2. Simulate cache invalidation**
```bash
docker exec food-ordering-platform-redis-1 redis-cli FLUSHALL
# Now repeat a cached query — it'll hit the LLM again
```

**3. Watch Kafka consumer lag**
```bash
docker exec food-ordering-platform-kafka-1 \
  kafka-consumer-groups --bootstrap-server localhost:9092 \
  --describe --group feedback-consumer-group
```

**4. Add a new fraud rule**
Edit `services/fraud-service/app.py`, add a keyword to `FRAUD_KEYWORDS`, rebuild:
```bash
docker-compose up --build -d fraud-service
```

**5. Test rate limiting**
```bash
# 12 rapid requests from same user — last 2 should be blocked
for i in $(seq 1 12); do
  echo -n "Request $i: "
  curl -s -X POST "http://localhost:8000/predict?v=v1" \
    -H "Content-Type: application/json" \
    -d '{"input": "pizza", "user_id": "rate_test"}' \
    | grep -o '"detail":"[^"]*"\|"model_version":"[^"]*"' | head -1 | cut -d'"' -f4
done
```

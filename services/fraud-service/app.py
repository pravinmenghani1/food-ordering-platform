from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Fraud Detection Service")

# ── Rule-based signals ────────────────────────────────────────────────────────
FRAUD_KEYWORDS = {"free money", "hack", "exploit", "bypass", "unlimited", "cheat"}
HIGH_RISK_PATTERNS = ["order cancel refund", "multiple accounts", "stolen card"]

class FraudIn(BaseModel):
    input: str
    user_id: str
    order_amount: Optional[float] = 0.0

def _score(text: str, amount: float) -> tuple[float, str]:
    score = 0.0
    reasons = []

    text_lower = text.lower()
    for kw in FRAUD_KEYWORDS:
        if kw in text_lower:
            score += 0.4
            reasons.append(f"keyword: '{kw}'")

    for pat in HIGH_RISK_PATTERNS:
        if any(w in text_lower for w in pat.split()):
            score += 0.2
            reasons.append(f"pattern: '{pat}'")

    if amount > 5000:
        score += 0.3
        reasons.append("unusually high order amount")

    return min(score, 1.0), "; ".join(reasons) or "no suspicious signals"

@app.post("/detect")
def detect(req: FraudIn):
    score, reason = _score(req.input, req.order_amount)
    return {
        "is_fraud": score >= 0.5,
        "fraud_score": round(score, 2),
        "reason": reason,
    }

@app.get("/health")
def health():
    return {"status": "ok"}

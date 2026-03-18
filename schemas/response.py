from pydantic import BaseModel
from typing import Optional

class PredictResponse(BaseModel):
    prediction: str
    confidence: float
    trace_id: str
    model_version: str
    cached: bool = False
    latency_ms: float

class FraudResponse(BaseModel):
    is_fraud: bool
    fraud_score: float
    reason: str
    trace_id: str

class ImageResponse(BaseModel):
    item_name: str
    image_url: str
    source: str          # "legacy" | "ai_generated"
    prompt_used: Optional[str] = None

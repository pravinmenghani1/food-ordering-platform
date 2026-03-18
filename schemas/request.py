from pydantic import BaseModel
from typing import Optional

class PredictRequest(BaseModel):
    input: str
    user_id: str
    model_version: Optional[str] = None  # override A/B routing

class FraudRequest(BaseModel):
    input: str
    user_id: str
    order_amount: Optional[float] = 0.0

class FeedbackRequest(BaseModel):
    trace_id: str
    user_id: str
    rating: int          # 1-5
    prediction: str
    was_helpful: bool

class ImageGenRequest(BaseModel):
    item_name: str
    description: Optional[str] = ""

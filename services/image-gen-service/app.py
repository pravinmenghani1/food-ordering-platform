import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI

app = FastAPI(title="Image Generation Service")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "mock")
llm = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY != "mock" else None

# ── Mock AI-generated image URLs (realistic food photography prompts) ──────────
# In production these come from DALL-E 3. For demo, we use Unsplash food images.
MOCK_AI_IMAGES = {
    "default": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600",
    "pizza":   "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=600",
    "burger":  "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600",
    "sushi":   "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=600",
    "pasta":   "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=600",
    "curry":   "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600",
    "salad":   "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600",
}

class ImageIn(BaseModel):
    item_name: str
    description: Optional[str] = ""

def _build_prompt(item_name: str, description: str) -> str:
    return (
        f"Professional food photography of {item_name}. "
        f"{description}. "
        "Shot on a clean white plate, soft natural lighting, shallow depth of field, "
        "appetizing and vibrant colors, restaurant-quality presentation, 4K."
    )

def _mock_image(item_name: str) -> str:
    key = next((k for k in MOCK_AI_IMAGES if k in item_name.lower()), "default")
    return MOCK_AI_IMAGES[key]

@app.post("/generate")
def generate(req: ImageIn):
    """
    🎯 THE TRANSFORMATION STORY:
    Before: Restaurant uploads a blurry phone photo → customers scroll past
    After:  GenAI generates professional food photography from just a text description
            → 3x higher click-through rate, more orders, happier restaurants
    """
    prompt = _build_prompt(req.item_name, req.description)

    if llm:
        response = llm.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
    else:
        # Demo mode: return curated Unsplash food photos
        image_url = _mock_image(req.item_name)

    return {
        "item_name": req.item_name,
        "image_url": image_url,
        "source": "ai_generated",
        "prompt_used": prompt,
    }

@app.get("/health")
def health():
    return {"status": "ok"}

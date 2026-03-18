import re
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Preprocessing Service")

class TextIn(BaseModel):
    text: str

STOP_WORDS = {"i", "me", "my", "the", "a", "an", "is", "are", "was"}

@app.post("/preprocess")
def preprocess(body: TextIn):
    text = body.text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)          # remove punctuation
    tokens = [w for w in text.split() if w not in STOP_WORDS]
    return {"text": " ".join(tokens), "token_count": len(tokens)}

@app.get("/health")
def health():
    return {"status": "ok"}

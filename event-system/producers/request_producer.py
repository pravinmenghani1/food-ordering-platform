import json, os
from kafka import KafkaProducer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v).encode(),
)

def publish(topic: str, payload: dict):
    future = producer.send(topic, payload)
    producer.flush()
    return future.get(timeout=10)

# ── Demo: manually publish a test event ──────────────────────────────────────
if __name__ == "__main__":
    publish("food-requests", {
        "user_id": "demo_user",
        "input": "I love spicy food",
        "trace_id": "abc-123",
    })
    print("✅ Event published to food-requests")

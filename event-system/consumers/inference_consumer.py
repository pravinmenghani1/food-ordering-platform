"""
Inference Consumer — listens to food-requests topic.
In a real system this would trigger async model inference,
store results in a DB, and update recommendation models.
"""
import json, os, time
from kafka import KafkaConsumer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

consumer = KafkaConsumer(
    "food-requests",
    bootstrap_servers=KAFKA_BOOTSTRAP,
    value_deserializer=lambda m: json.loads(m.decode()),
    group_id="inference-consumer-group",
    auto_offset_reset="earliest",
)

print("🎧 Inference consumer listening on food-requests...")
for msg in consumer:
    event = msg.value
    print(f"[{time.strftime('%H:%M:%S')}] Processing: user={event.get('user_id')} "
          f"trace={event.get('trace_id')} model={event.get('model_version')}")
    # In production: store to DB, update embeddings, trigger retraining signals

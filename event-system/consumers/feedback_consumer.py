"""
Feedback Consumer — closes the AI feedback loop.
Listens to feedback-events and fraud-alerts topics.
In production: feeds into model fine-tuning, updates user preference embeddings.
"""
import json, os, time
from collections import defaultdict
from kafka import KafkaConsumer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

def make_consumer(retries=10):
    for i in range(retries):
        try:
            return KafkaConsumer(
                "feedback-events",
                "fraud-alerts",
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_deserializer=lambda m: json.loads(m.decode()),
                group_id="feedback-consumer-group",
                auto_offset_reset="earliest",
            )
        except Exception as e:
            print(f"[{i+1}/{retries}] Kafka not ready: {e}. Retrying in 5s...")
            time.sleep(5)
    raise RuntimeError("Could not connect to Kafka after retries")

consumer = make_consumer()
stats = defaultdict(int)
print("🎧 Feedback consumer listening on feedback-events + fraud-alerts...")
for msg in consumer:
    topic = msg.topic
    event = msg.value

    if topic == "feedback-events":
        rating = event.get("rating", 0)
        stats["total_feedback"] += 1
        stats["rating_sum"] += rating
        avg = stats["rating_sum"] / stats["total_feedback"]
        print(f"[FEEDBACK] user={event.get('user_id')} rating={rating}/5 "
              f"avg_rating={avg:.2f} helpful={event.get('was_helpful')}")

    elif topic == "fraud-alerts":
        stats["fraud_count"] += 1
        print(f"[FRAUD ALERT] user={event.get('user_id')} "
              f"score={event.get('fraud_score')} reason={event.get('reason')}")

import json
import time
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify
from flask_cors import CORS
from confluent_kafka import Producer, Consumer, KafkaError

from app_config import config
from pipeline import run_verification_pipeline

app = Flask(__name__)
CORS(app, origins=config["cors_origins"], supports_credentials=True)

producer = None
consumer_thread = None


def get_producer():
    global producer
    if producer is None:
        producer = Producer({
            "bootstrap.servers": ",".join(config["kafka_brokers"]),
            "client.id": config["service_name"],
        })
    return producer


def process_message(message: dict):
    print(f"[{config['service_name']}] Processing verification for {message.get('postId')} (source: {message.get('source')})")

    result = run_verification_pipeline(message)

    print(f"[{config['service_name']}] Verification complete: {result['status']} (trust: {result['finalTrustRating']})")

    p = get_producer()
    p.produce(
        config["output_topic"],
        key=result["submissionId"],
        value=json.dumps(result).encode("utf-8"),
    )
    p.flush()

    print(f"[{config['service_name']}] Published result on {config['output_topic']}")


def start_consumer():
    consumer = Consumer({
        "bootstrap.servers": ",".join(config["kafka_brokers"]),
        "group.id": config["consumer_group"],
        "auto.offset.reset": "earliest",
        "client.id": f"{config['service_name']}-consumer",
    })

    consumer.subscribe([config["input_topic"]])
    print(f"[{config['service_name']}] Subscribed to {config['input_topic']}")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print(f"[{config['service_name']}] Consumer error: {msg.error()}")
                continue

            try:
                value = json.loads(msg.value().decode("utf-8"))
                process_message(value)
            except Exception as e:
                print(f"[{config['service_name']}] Error processing message: {e}")

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()


@app.get("/health")
def health():
    return jsonify({
        "service": config["service_name"],
        "status": "ok",
        "mode": "kafka-consumer-worker",
        "input_topic": config["input_topic"],
        "output_topic": config["output_topic"],
        "timestamp": time.time(),
    })


if __name__ == "__main__":
    # Start Kafka consumer in background thread
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()
    print(f"[{config['service_name']}] Kafka consumer started")

    try:
        get_producer()
        print(f"[{config['service_name']}] Kafka producer connected")
    except Exception as e:
        print(f"[{config['service_name']}] Kafka producer connection failed: {e}")

    app.run(port=config["port"])
import os

def split_csv(value, fallback):
    if value:
        return [item.strip() for item in value.split(",") if item.strip()]
    return fallback

config = {
    "service_name": "content-verification-service",
    "port": int(os.environ.get("PORT", 8082)),
    "cors_origins": split_csv(os.environ.get("CORS_ORIGINS"), ["http://localhost:3000"]),
    "kafka_brokers": split_csv(os.environ.get("KAFKA_BROKERS"), [
        "localhost:9094", "localhost:9095", "localhost:9096"
    ]),
    "input_topic": os.environ.get("INPUT_TOPIC", "content-verification.requested"),
    "output_topic": os.environ.get("OUTPUT_TOPIC", "content-verification.completed"),
    "consumer_group": os.environ.get("CONSUMER_GROUP", "content-verification-service-group"),
    "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
}
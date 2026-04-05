import os

def split_csv(value, fallback):
    if value:
        return [item.strip() for item in value.split(",") if item.strip()]
    return fallback

config = {
    "service_name": "source-verification-service",
    "port": int(os.environ.get("PORT", 8080)),
    "cors_origins": split_csv(os.environ.get("CORS_ORIGINS"), ["http://localhost:3000"]),
    "kafka_brokers": split_csv(os.environ.get("KAFKA_BROKERS"), [
        "localhost:9094", "localhost:9095", "localhost:9096"
    ]),
    "kafka_topic": os.environ.get("CONTENT_VERIFICATION_TOPIC", "content-verification.requested"),
    "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
}
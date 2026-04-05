import json
import time
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_cors import CORS
from confluent_kafka import Producer

from app_config import config
from agent.source_agent import SourceAgent

app = Flask(__name__)
CORS(app, origins=config["cors_origins"], supports_credentials=True)

producer = None
agent = SourceAgent(api_key=config["gemini_api_key"], verbose=False)


def get_producer():
    global producer
    if producer is None:
        producer = Producer({
            "bootstrap.servers": ",".join(config["kafka_brokers"]),
            "client.id": config["service_name"],
        })
    return producer


def normalize_source(payload):
    raw = payload.get("sourceUrl") or payload.get("sourceAccountId") or ""
    return raw.strip().lower()


@app.get("/health")
def health():
    return jsonify({
        "service": config["service_name"],
        "status": "ok",
        "timestamp": time.time(),
    })


@app.post("/verify")
def verify():
    payload = request.get_json() or {}
    normalized_source = normalize_source(payload)

    if not normalized_source:
        return jsonify({"message": "sourceUrl or sourceAccountId is required"}), 400

    try:
        # Run the 3-layer source agent
        agent_result = agent.run(
            url=payload.get("sourceUrl"),
            text=payload.get("narrative"),
            metadata=payload.get("metadata"),
        )

        # Map agent risk to service status
        status_map = {"Low": "verified", "Medium": "suspicious", "High": "unverifiable"}
        status = status_map.get(agent_result["risk"], "suspicious")

        # Invert suspicion score to trust rating (0-100 → 0.0-1.0)
        trust_rating = round(1 - agent_result["score"] / 100, 2)

        # Escalate to Kafka if not verified
        kafka_escalated = False
        if status != "verified":
            verification_request = {
                "postId": payload.get("postId") or f"post-{time.time()}",
                "source": normalized_source,
                "narrative": payload.get("narrative"),
                "contentType": payload.get("contentType", "mixed"),
                "requestedAt": datetime.now(timezone.utc).isoformat(),
                "reason": "source-agent-escalation",
            }
            try:
                p = get_producer()
                p.produce(
                    config["kafka_topic"],
                    key=verification_request["postId"],
                    value=json.dumps(verification_request).encode("utf-8"),
                )
                p.flush()
                kafka_escalated = True
            except Exception as e:
                app.logger.warning(f"Kafka escalation failed: {e}")

        return jsonify({
            "source": normalized_source,
            "status": status,
            "trustRating": trust_rating,
            "risk": agent_result["risk"],
            "score": agent_result["score"],
            "reasons": agent_result["reasons"],
            "details": agent_result["details"],
            "verificationMode": "source-agent",
            "kafkaEscalated": kafka_escalated,
            "topic": config["kafka_topic"] if kafka_escalated else None,
        }), 200 if status == "verified" else 202

    except Exception as e:
        return jsonify({"message": str(e)}), 500


if __name__ == "__main__":
    try:
        get_producer()
        app.logger.info(f"[{config['service_name']}] Kafka producer connected")
    except Exception as e:
        app.logger.warning(f"Kafka producer connection failed: {e}")

    app.run(port=config["port"])
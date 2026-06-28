import uuid

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from audit import get_recent_entries, read_log, write_log_entry
from detector import analyze_text
from labels import attribution_from_score, label_for_attribution

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Provenance Guard API is running",
        "endpoints": ["/submit", "/appeal", "/log"]
    })


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json(silent=True) or {}

    text = data.get("text", "").strip()
    creator_id = data.get("creator_id", "").strip()

    if not text or not creator_id:
        return jsonify({
            "error": "Both 'text' and 'creator_id' are required."
        }), 400

    content_id = str(uuid.uuid4())

    scores = analyze_text(text)
    confidence = scores["confidence"]
    attribution = attribution_from_score(confidence)
    label = label_for_attribution(attribution)

    response = {
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": attribution,
        "confidence": confidence,
        "label": label,
        "signals": {
            "llm_score": scores["llm_score"],
            "stylometric_score": scores["stylometric_score"],
        },
        "status": "classified"
    }

    write_log_entry({
        "event_type": "classification",
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": attribution,
        "confidence": confidence,
        "llm_score": scores["llm_score"],
        "stylometric_score": scores["stylometric_score"],
        "label": label,
        "status": "classified"
    })

    return jsonify(response), 200


@app.route("/appeal", methods=["POST"])
def appeal():
    data = request.get_json(silent=True) or {}

    content_id = data.get("content_id", "").strip()
    creator_reasoning = data.get("creator_reasoning", "").strip()

    if not content_id or not creator_reasoning:
        return jsonify({
            "error": "Both 'content_id' and 'creator_reasoning' are required."
        }), 400

    logs = read_log()
    original = next(
        (
            entry for entry in reversed(logs)
            if entry.get("content_id") == content_id
            and entry.get("event_type") == "classification"
        ),
        None
    )

    if not original:
        return jsonify({
            "error": "No classified content found for that content_id."
        }), 404

    creator_id = original.get("creator_id", "unknown")

    write_log_entry({
        "event_type": "appeal",
        "content_id": content_id,
        "creator_id": creator_id,
        "appeal_reasoning": creator_reasoning,
        "original_attribution": original.get("attribution"),
        "original_confidence": original.get("confidence"),
        "status": "under_review"
    })

    return jsonify({
        "content_id": content_id,
        "creator_id": creator_id,
        "status": "under_review",
        "message": "Appeal received and logged for review."
    }), 200


@app.route("/log", methods=["GET"])
def log():
    return jsonify({
        "entries": get_recent_entries()
    }), 200


if __name__ == "__main__":
    app.run(debug=True)
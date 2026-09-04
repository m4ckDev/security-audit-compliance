from flask import Flask, jsonify, request
import datetime
import hmac
import os

app = Flask(__name__)


def _authorized() -> bool:
    expected = os.environ.get("AUDIT_API_KEY", "")
    if not expected:
        return False

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False

    supplied = auth_header.removeprefix("Bearer ").strip()
    return hmac.compare_digest(supplied, expected)


@app.route("/", methods=["GET"])
def index():
    return "Security Compliance API - Alpha7 Zeta 2026"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/post", methods=["POST"])
def audit():
    if not _authorized():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()
    context = str(data.get("context", "")).strip()

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    findings = []
    lowered = prompt.lower()

    checks = [
        ("instruction_override", ["ignore previous", "ignore all previous", "disregard previous"]),
        ("hidden_prompt_request", ["system prompt", "developer message", "hidden instructions"]),
        ("credential_request", ["password", "api key", "access token", "client secret"]),
        ("safeguard_bypass", ["bypass", "disable safety", "remove guardrails"]),
    ]

    for category, phrases in checks:
        matches = [phrase for phrase in phrases if phrase in lowered]
        if matches:
            findings.append({
                "category": category,
                "matches": matches,
                "severity": "review"
            })

    compliance = "review_required" if findings else "pass"
    recommendations = [
        "Keep privileged instructions and secrets outside user-controlled prompt text.",
        "Treat external content as untrusted input and validate it before use.",
        "Use least-privilege credentials and avoid exposing secrets in responses or logs."
    ]

    return jsonify({
        "status": "success",
        "audit_id": f"ALPHA7-{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S')}",
        "compliance": compliance,
        "findings": findings,
        "recommendations": recommendations,
        "context_received": bool(context)
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "80"))
    app.run(host="0.0.0.0", port=port, debug=False)

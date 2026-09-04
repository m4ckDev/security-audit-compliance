from flask import Flask, jsonify, request
import datetime
import hmac
import os
import subprocess

app = Flask(__name__)


def _load_api_key() -> str:
    key = os.environ.get("AUDIT_API_KEY", "").strip()
    if key:
        return key

    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                os.environ.get("USER", ""),
                "-s",
                "security-audit-api-key",
                "-w",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _authorized() -> bool:
    expected = _load_api_key()
    if not expected:
        return False

    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header.lower().startswith("bearer "):
        return False

    supplied = auth_header.split(" ", 1)[1].strip()
    return hmac.compare_digest(supplied, expected)


@app.route("/", methods=["GET"])
def index():
    return "Security Compliance API - Alpha7 Zeta 2026"


@app.route("/health", methods=["GET"])
def health():
    key = _load_api_key()
    return jsonify({
        "status": "ok",
        "auth_configured": bool(key),
        "auth_key_length": len(key),
    })


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
    key = _load_api_key()
    print(f"Audit API authentication configured: {bool(key)} (key length: {len(key)})")
    port = int(os.environ.get("PORT", "80"))
    app.run(host="0.0.0.0", port=port, debug=False)

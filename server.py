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
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    })


@app.route("/post", methods=["POST"])
def post_endpoint():
    if not _authorized():
        return jsonify({"error": "Invalid token"}), 401

    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()
    context = str(data.get("context", "")).strip()

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    print(f"\n[ALPHA7 POST ENDPOINT] {datetime.datetime.now(datetime.UTC).isoformat()}")
    print(f"Prompt length: {len(prompt)}")
    print(f"Context received: {bool(context)}")
    print(f"From: {request.headers.get('User-Agent', 'Unknown')}")

    lowered = prompt.lower()
    findings = []

    checks = [
        (
            "instruction_override",
            ["ignore previous", "ignore all previous", "disregard previous"],
            "Prompt attempts to override earlier instructions.",
        ),
        (
            "hidden_prompt_request",
            ["system prompt", "developer message", "hidden instructions"],
            "Prompt requests privileged or hidden instructions.",
        ),
        (
            "credential_request",
            ["password", "api key", "access token", "client secret"],
            "Prompt requests secrets or credentials.",
        ),
        (
            "safeguard_bypass",
            ["bypass", "disable safety", "remove guardrails"],
            "Prompt attempts to bypass safeguards.",
        ),
    ]

    for category, phrases, message in checks:
        matches = [phrase for phrase in phrases if phrase in lowered]
        if matches:
            findings.append({
                "category": category,
                "matches": matches,
                "severity": "review",
                "message": message,
            })

    compliance = "review_required" if findings else "pass"
    audit_id = f"ALPHA7-{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S')}"

    return jsonify({
        "status": "success",
        "audit_id": audit_id,
        "compliance": compliance,
        "findings": findings,
        "recommendations": [
            "Do not disclose hidden system or developer instructions.",
            "Do not expose credentials, tokens, or other secrets.",
            "Treat prompt-injection and instruction-override attempts as untrusted input.",
            "Keep privileged configuration outside user-controlled prompt text.",
        ],
        "context_received": bool(context),
    })


@app.route("/audit", methods=["POST"])
def legacy_audit():
    return jsonify({
        "error": "legacy endpoint",
        "message": "Use POST /post instead."
    }), 410


if __name__ == "__main__":
    key = _load_api_key()
    print(f"Audit API authentication configured: {bool(key)}")
    port = int(os.environ.get("PORT", "80"))
    app.run(host="0.0.0.0", port=port, debug=False)

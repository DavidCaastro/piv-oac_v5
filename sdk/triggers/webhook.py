"""sdk/triggers/webhook.py — HTTP webhook trigger for PIV/OAC sessions.

Starts a lightweight HTTP server that receives objectives via POST requests.
Useful for Slack, Jira, Linear, or any external system integration.

Usage:
    piv trigger webhook --port=8765

Request format:
    POST /session
    Content-Type: application/json
    X-PIV-Signature: hmac-sha256=<signature>   (if webhook_secret configured)

    {
      "objective": "add JWT authentication to the REST API",
      "provider": "anthropic",
      "answers": {}          // optional pre-supplied answers
    }

Response:
    {
      "session_id": "...",
      "status": "accepted",
      "message": "Session started asynchronously"
    }
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any


class WebhookError(Exception):
    pass


def _verify_signature(body: bytes, signature_header: str, secret: str) -> bool:
    """Verify HMAC-SHA256 webhook signature (Tier 1)."""
    if not signature_header.startswith("hmac-sha256="):
        return False
    received = signature_header.removeprefix("hmac-sha256=")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received, expected)


class _PIVHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler — no framework, no LLM, just routing."""

    webhook_secret: str | None = None
    repo_root: Path = Path.cwd()

    def do_POST(self) -> None:
        if self.path != "/session":
            self._respond(404, {"error": "not_found"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Signature check (if secret configured)
        secret = self.__class__.webhook_secret
        if secret:
            sig = self.headers.get("X-PIV-Signature", "")
            if not _verify_signature(body, sig, secret):
                self._respond(401, {"error": "invalid_signature"})
                return

        try:
            payload: dict[str, Any] = json.loads(body)
        except json.JSONDecodeError:
            self._respond(400, {"error": "invalid_json"})
            return

        objective = payload.get("objective", "").strip()
        if not objective:
            self._respond(400, {"error": "objective_required"})
            return

        provider = payload.get("provider", "anthropic")
        answers = payload.get("answers") or None

        # Fire-and-forget: run session in background thread
        session_id_placeholder = _fire_session(
            objective=objective,
            provider=provider,
            answers=answers,
            repo_root=self.__class__.repo_root,
        )

        self._respond(202, {
            "session_id": session_id_placeholder,
            "status": "accepted",
            "message": "Session started asynchronously. Monitor logs/ for progress.",
        })

    def do_GET(self) -> None:
        if self.path == "/health":
            self._respond(200, {"status": "ok", "service": "piv-oac-webhook"})
        else:
            self._respond(404, {"error": "not_found"})

    def _respond(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        # Route to piv log format instead of default stderr
        print(f"[piv-webhook] {self.address_string()} - {fmt % args}")


def _fire_session(
    objective: str,
    provider: str,
    answers: dict | None,
    repo_root: Path,
) -> str:
    """Start an AsyncSession in a daemon thread. Returns a placeholder session id."""
    import uuid

    placeholder_id = str(uuid.uuid4())

    def _run() -> None:
        from sdk.core.session_async import AsyncSession

        async def _async_run() -> None:
            session = AsyncSession.init(provider=provider, repo_root=repo_root)
            result = await session.run_async(objective=objective, answers=answers)
            print(
                f"[piv-webhook] session={result.session_id} "
                f"status={result.status} tokens={result.total_tokens}"
            )

        asyncio.run(_async_run())

    thread = Thread(target=_run, daemon=True)
    thread.start()
    return placeholder_id


def start_webhook_server(port: int = 8765, repo_root: Path | None = None) -> None:
    """Start the PIV/OAC webhook HTTP server (blocking).

    Secret is read from env var PIV_WEBHOOK_SECRET (optional).
    """
    _PIVHandler.webhook_secret = os.environ.get("PIV_WEBHOOK_SECRET")
    _PIVHandler.repo_root = repo_root or Path.cwd()

    server = HTTPServer(("0.0.0.0", port), _PIVHandler)
    print(f"[piv-webhook] listening on :{port}")
    print(f"[piv-webhook] POST http://localhost:{port}/session")
    print(f"[piv-webhook] GET  http://localhost:{port}/health")
    if _PIVHandler.webhook_secret:
        print("[piv-webhook] HMAC-SHA256 signature validation: ENABLED")
    else:
        print("[piv-webhook] WARNING: no webhook secret set — requests not verified")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[piv-webhook] shutting down")
        server.shutdown()

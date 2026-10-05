from __future__ import annotations

import hashlib
import hmac
import secrets
import time


def issue_conversation_token() -> str:
    return secrets.token_urlsafe(32)


def issue_visitor_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_conversation_token(token: str, pepper: str) -> str:
    return hmac.new(pepper.encode(), token.encode(), hashlib.sha256).hexdigest()


def verify_secret(candidate: str, expected: str) -> bool:
    return hmac.compare_digest(candidate.encode(), expected.encode())


def issue_admin_session(secret: str) -> str:
    issued_at = str(int(time.time()))
    signature = hmac.new(
        secret.encode(), f"admin:{issued_at}".encode(), hashlib.sha256
    ).hexdigest()
    return f"{issued_at}.{signature}"


def verify_admin_session(token: str, secret: str, max_age_seconds: int) -> bool:
    try:
        issued_at_raw, signature = token.split(".", 1)
        issued_at = int(issued_at_raw)
    except (ValueError, AttributeError):
        return False
    age = int(time.time()) - issued_at
    if age < 0 or age > max_age_seconds:
        return False
    expected = hmac.new(
        secret.encode(), f"admin:{issued_at_raw}".encode(), hashlib.sha256
    ).hexdigest()
    return verify_secret(signature, expected)


def content_hash(value: str | bytes) -> str:
    payload = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(payload).hexdigest()

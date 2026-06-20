from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from .config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_token(subject: str, role: str, expire_days: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=expire_days)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_device_token(serial: str) -> str:
    return create_token(serial, "device", settings.device_token_expire_days)


def create_user_token(email: str) -> str:
    return create_token(email, "user", settings.user_token_expire_days)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def generate_pairing_code() -> str:
    return str(secrets.randbelow(900000) + 100000)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


# Sessions are stored in a module-level dict for V1 (single-process).
# Replace with Redis in production.
_sessions: dict[str, str] = {}  # token → email


def create_session(email: str) -> str:
    token = generate_session_token()
    _sessions[token] = email
    return token


def get_session_email(token: str) -> str | None:
    return _sessions.get(token)


def delete_session(token: str) -> None:
    _sessions.pop(token, None)

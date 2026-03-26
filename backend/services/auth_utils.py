"""
认证与权限工具
"""
import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Header, HTTPException
from backend.database import get_connection


TOKEN_TTL_DAYS = 7
PBKDF2_ROUNDS = 120_000
MIN_PASSWORD_LEN = 8


def _now_utc_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def validate_password_strength(password: str):
    pwd = (password or "").strip()
    if len(pwd) < MIN_PASSWORD_LEN:
        raise HTTPException(status_code=400, detail=f"密码长度至少 {MIN_PASSWORD_LEN} 位")


def verify_password(stored: str, password: str) -> bool:
    try:
        salt_b64, hash_b64 = stored.split("$", 1)
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(hash_b64.encode())
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
        return hmac.compare_digest(expected, dk)
    except Exception:
        return False


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(days=TOKEN_TTL_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO user_sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at)
        )
        conn.commit()
    finally:
        conn.close()
    return token


def get_user_by_token(token: str) -> Optional[dict]:
    if not token:
        return None
    now = _now_utc_str()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT u.*, s.expires_at FROM users u "
            "JOIN user_sessions s ON s.user_id = u.id "
            "WHERE s.token = ? AND s.expires_at > ?",
            (token, now)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_session(token: str):
    if not token:
        return
    conn = get_connection()
    try:
        conn.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


def delete_user_sessions(user_id: int, except_token: Optional[str] = None) -> int:
    conn = get_connection()
    try:
        if except_token:
            cur = conn.execute(
                "DELETE FROM user_sessions WHERE user_id = ? AND token != ?",
                (user_id, except_token)
            )
        else:
            cur = conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
        conn.commit()
        return cur.rowcount or 0
    finally:
        conn.close()


def count_active_sessions(user_id: int) -> int:
    now = _now_utc_str()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM user_sessions WHERE user_id = ? AND expires_at > ?",
            (user_id, now)
        ).fetchone()
        return int(row["cnt"] if row else 0)
    finally:
        conn.close()


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization.split(" ", 1)[1].strip()
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期")
    return user


def get_token_from_header(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="无权限")


def require_roles(user: dict, allowed_roles: set[str]):
    if user.get("role") not in allowed_roles:
        raise HTTPException(status_code=403, detail="无权限")

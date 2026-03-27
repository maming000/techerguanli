"""
登录与会话管理
"""
import time
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel
from backend.database import get_connection
from backend.services.auth_utils import (
    verify_password,
    create_session,
    delete_session,
    get_current_user,
    get_token_from_header,
    delete_user_sessions,
    validate_password_strength,
)

router = APIRouter(prefix="/api/auth", tags=["认证"])

LOGIN_FAIL_WINDOW_SECONDS = 3 * 60
LOGIN_FAIL_MAX = 5
LOGIN_BLOCK_SECONDS = 4 * 60 * 60


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    username: str
    id_card_last6: str
    new_password: str


def get_client_ip(request: Request) -> str:
    # 兼容 Nginx/宝塔反代场景
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    x_real_ip = (request.headers.get("x-real-ip") or "").strip()
    if x_real_ip:
        return x_real_ip
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def get_ip_limit_row(conn, ip: str) -> dict | None:
    row = conn.execute(
        "SELECT ip, failed_count, window_start_ts, blocked_until_ts FROM login_rate_limits WHERE ip = ?",
        (ip,),
    ).fetchone()
    return dict(row) if row else None


def clear_ip_failures(conn, ip: str) -> None:
    conn.execute(
        "INSERT INTO login_rate_limits (ip, failed_count, window_start_ts, blocked_until_ts, updated_at) "
        "VALUES (?, 0, NULL, NULL, CURRENT_TIMESTAMP) "
        "ON CONFLICT(ip) DO UPDATE SET failed_count = 0, window_start_ts = NULL, blocked_until_ts = NULL, updated_at = CURRENT_TIMESTAMP",
        (ip,),
    )


def record_ip_failure(conn, ip: str, now_ts: int) -> tuple[bool, int]:
    """
    记录失败并返回：
    - is_blocked_now: 是否在本次失败后触发封禁
    - blocked_until_ts: 封禁截至时间（未封禁则为 0）
    """
    row = get_ip_limit_row(conn, ip)
    if not row:
        conn.execute(
            "INSERT INTO login_rate_limits (ip, failed_count, window_start_ts, blocked_until_ts, updated_at) "
            "VALUES (?, 1, ?, NULL, CURRENT_TIMESTAMP)",
            (ip, now_ts),
        )
        return False, 0

    window_start = row.get("window_start_ts")
    failed_count = int(row.get("failed_count") or 0)
    blocked_until = int(row.get("blocked_until_ts") or 0)

    # 已过封禁时间：先清状态再按新失败计
    if blocked_until and now_ts >= blocked_until:
        failed_count = 0
        window_start = None
        blocked_until = 0

    # 超过失败统计窗口：重置为新的窗口
    if not window_start or (now_ts - int(window_start)) > LOGIN_FAIL_WINDOW_SECONDS:
        failed_count = 1
        window_start = now_ts
    else:
        failed_count += 1

    trigger_block = failed_count >= LOGIN_FAIL_MAX and (now_ts - int(window_start)) <= LOGIN_FAIL_WINDOW_SECONDS
    if trigger_block:
        blocked_until = now_ts + LOGIN_BLOCK_SECONDS
        conn.execute(
            "UPDATE login_rate_limits SET failed_count = ?, window_start_ts = ?, blocked_until_ts = ?, updated_at = CURRENT_TIMESTAMP WHERE ip = ?",
            (failed_count, window_start, blocked_until, ip),
        )
        return True, blocked_until

    conn.execute(
        "UPDATE login_rate_limits SET failed_count = ?, window_start_ts = ?, blocked_until_ts = NULL, updated_at = CURRENT_TIMESTAMP WHERE ip = ?",
        (failed_count, window_start, ip),
    )
    return False, 0


@router.post("/login")
async def login(data: LoginRequest, request: Request):
    conn = get_connection()
    try:
        now_ts = int(time.time())
        client_ip = get_client_ip(request)
        ip_limit = get_ip_limit_row(conn, client_ip)
        blocked_until = int((ip_limit or {}).get("blocked_until_ts") or 0)
        if blocked_until and now_ts < blocked_until:
            remain_seconds = blocked_until - now_ts
            remain_minutes = max(1, (remain_seconds + 59) // 60)
            raise HTTPException(
                status_code=429,
                detail=f"该IP登录失败次数过多，已被限制登录。请约{remain_minutes}分钟后再试。"
            )

        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (data.username.strip(),)
        ).fetchone()
        if not row:
            blocked, blocked_until_ts = record_ip_failure(conn, client_ip, now_ts)
            conn.commit()
            if blocked:
                remain_minutes = max(1, (blocked_until_ts - now_ts + 59) // 60)
                raise HTTPException(status_code=429, detail=f"该IP登录失败次数过多，已被限制登录。请约{remain_minutes}分钟后再试。")
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        user = dict(row)
        if not verify_password(user["password_hash"], data.password):
            blocked, blocked_until_ts = record_ip_failure(conn, client_ip, now_ts)
            conn.commit()
            if blocked:
                remain_minutes = max(1, (blocked_until_ts - now_ts + 59) // 60)
                raise HTTPException(status_code=429, detail=f"该IP登录失败次数过多，已被限制登录。请约{remain_minutes}分钟后再试。")
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        clear_ip_failures(conn, client_ip)
        conn.commit()
        token = create_session(user["id"])
        teacher_name = None
        if user.get("teacher_id"):
            t = conn.execute("SELECT name FROM teachers WHERE id = ?", (user["teacher_id"],)).fetchone()
            if t:
                teacher_name = t["name"]
        return {
            "token": token,
            "role": user["role"],
            "teacher_id": user.get("teacher_id"),
            "name": teacher_name,
            "username": user["username"],
        }
    finally:
        conn.close()


@router.post("/logout")
async def logout(authorization: str | None = Header(None), user=Depends(get_current_user)):
    token = get_token_from_header(authorization)
    if token:
        delete_session(token)
    return {"message": "已退出"}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "teacher_id": user.get("teacher_id"),
    }


@router.post("/change-password")
async def change_password(data: ChangePasswordRequest, user=Depends(get_current_user)):
    validate_password_strength(data.new_password)
    if data.new_password == data.old_password:
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")

    conn = get_connection()
    try:
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        if not verify_password(row["password_hash"], data.old_password):
            raise HTTPException(status_code=400, detail="旧密码不正确")
        from backend.services.auth_utils import hash_password
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(data.new_password), user["id"])
        )
        conn.commit()
        delete_user_sessions(user["id"])
        return {"message": "密码已修改"}
    finally:
        conn.close()


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    """
    教师忘记密码重置：使用账号 + 身份证后6位验证
    """
    username = data.username.strip()
    id_last6 = data.id_card_last6.strip().upper()
    validate_password_strength(data.new_password)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT u.id, u.role, u.teacher_id, t.id_card "
            "FROM users u LEFT JOIN teachers t ON t.id = u.teacher_id "
            "WHERE u.username = ?",
            (username,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="账号不存在")
        if row["role"] != "teacher":
            raise HTTPException(status_code=403, detail="仅教师账号可使用此功能")
        id_card = (row["id_card"] or "").strip().upper()
        if not id_card or len(id_card) < 6:
            raise HTTPException(status_code=400, detail="教师身份证信息不完整")
        if id_card[-6:] != id_last6:
            raise HTTPException(status_code=400, detail="身份证后6位不匹配")

        from backend.services.auth_utils import hash_password
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(data.new_password), row["id"])
        )
        conn.commit()
        return {"message": "密码已重置"}
    finally:
        conn.close()

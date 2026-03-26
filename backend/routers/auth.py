"""
登录与会话管理
"""
from fastapi import APIRouter, HTTPException, Depends, Header
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


@router.post("/login")
async def login(data: LoginRequest):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (data.username.strip(),)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        user = dict(row)
        if not verify_password(user["password_hash"], data.password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
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

"""
账号管理（管理员）
"""
import secrets
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
from pydantic import BaseModel
from backend.database import get_connection
from backend.services.auth_utils import (
    get_current_user,
    require_admin,
    hash_password,
    delete_user_sessions,
    count_active_sessions,
    validate_password_strength,
)
from backend.config import EXPORT_DIR

router = APIRouter(prefix="/api/users", tags=["账号管理"])


class CreateTeacherUser(BaseModel):
    teacher_id: int
    username: str | None = None
    password: str | None = None


class ResetPasswordRequest(BaseModel):
    password: str | None = None


class CreateViewerUser(BaseModel):
    username: str
    password: str


@router.get("/")
async def list_users(user=Depends(get_current_user)):
    require_admin(user)
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, username, role, teacher_id, created_at FROM users ORDER BY id DESC"
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["active_sessions"] = count_active_sessions(item["id"])
            result.append(item)
        return result
    finally:
        conn.close()


@router.post("/viewer")
async def create_viewer_user(data: CreateViewerUser, user=Depends(get_current_user)):
    require_admin(user)
    username = (data.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    validate_password_strength(data.password)

    conn = get_connection()
    try:
        existed = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existed:
            raise HTTPException(status_code=400, detail="用户名已存在")
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'viewer')",
            (username, hash_password(data.password))
        )
        conn.commit()
        return {"username": username, "role": "viewer"}
    finally:
        conn.close()


@router.get("/teacher/{teacher_id}")
async def get_teacher_user(teacher_id: int, user=Depends(get_current_user)):
    require_admin(user)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, username, role, teacher_id, created_at FROM users WHERE teacher_id = ?",
            (teacher_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


@router.post("/teacher")
async def create_teacher_user(data: CreateTeacherUser, user=Depends(get_current_user)):
    require_admin(user)
    conn = get_connection()
    try:
        t = conn.execute("SELECT id, name FROM teachers WHERE id = ?", (data.teacher_id,)).fetchone()
        if not t:
            raise HTTPException(status_code=404, detail="教师不存在")

        existing = conn.execute(
            "SELECT id FROM users WHERE teacher_id = ?",
            (data.teacher_id,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="该教师已存在账号")

        username = (data.username or f"t{data.teacher_id}").strip()
        password = data.password or secrets.token_urlsafe(8)
        validate_password_strength(password)

        conn.execute(
            "INSERT INTO users (username, password_hash, role, teacher_id) VALUES (?, ?, 'teacher', ?)",
            (username, hash_password(password), data.teacher_id)
        )
        conn.commit()
        return {
            "username": username,
            "password": password,
            "teacher_id": data.teacher_id,
            "teacher_name": t["name"]
        }
    finally:
        conn.close()


@router.post("/{user_id}/reset-password")
async def reset_password(user_id: int, data: ResetPasswordRequest, user=Depends(get_current_user)):
    require_admin(user)
    new_password = data.password or secrets.token_urlsafe(8)
    validate_password_strength(new_password)
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), user_id)
        )
        conn.commit()
        deleted_sessions = delete_user_sessions(user_id)
        return {"password": new_password, "revoked_sessions": deleted_sessions}
    finally:
        conn.close()


@router.delete("/{user_id}")
async def delete_user(user_id: int, user=Depends(get_current_user)):
    require_admin(user)
    conn = get_connection()
    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return {"message": "已删除"}
    finally:
        conn.close()


@router.post("/{user_id}/revoke-sessions")
async def revoke_sessions(user_id: int, user=Depends(get_current_user)):
    require_admin(user)
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
    finally:
        conn.close()
    deleted = delete_user_sessions(user_id)
    return {"revoked_sessions": deleted}


@router.post("/bulk-create")
async def bulk_create_teacher_users(user=Depends(get_current_user)):
    require_admin(user)
    conn = get_connection()
    try:
        teachers = conn.execute(
            "SELECT id, name FROM teachers WHERE id NOT IN (SELECT teacher_id FROM users WHERE teacher_id IS NOT NULL)"
        ).fetchall()

        created = []
        for t in teachers:
            base_username = f"t{t['id']}"
            username = base_username
            suffix = 1
            while conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
                username = f"{base_username}{suffix}"
                suffix += 1

            password = secrets.token_urlsafe(8)
            validate_password_strength(password)
            conn.execute(
                "INSERT INTO users (username, password_hash, role, teacher_id) VALUES (?, ?, 'teacher', ?)",
                (username, hash_password(password), t["id"])
            )
            created.append({
                "teacher_id": t["id"],
                "teacher_name": t["name"],
                "username": username,
                "password": password
            })

        conn.commit()
        return {"created": created}
    finally:
        conn.close()


@router.post("/bulk-create-export")
async def bulk_create_teacher_users_export(user=Depends(get_current_user)):
    require_admin(user)
    conn = get_connection()
    try:
        teachers = conn.execute(
            "SELECT id, name FROM teachers WHERE id NOT IN (SELECT teacher_id FROM users WHERE teacher_id IS NOT NULL)"
        ).fetchall()

        created = []
        for t in teachers:
            base_username = f"t{t['id']}"
            username = base_username
            suffix = 1
            while conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
                username = f"{base_username}{suffix}"
                suffix += 1

            password = secrets.token_urlsafe(8)
            validate_password_strength(password)
            conn.execute(
                "INSERT INTO users (username, password_hash, role, teacher_id) VALUES (?, ?, 'teacher', ?)",
                (username, hash_password(password), t["id"])
            )
            created.append({
                "teacher_id": t["id"],
                "teacher_name": t["name"],
                "username": username,
                "password": password
            })

        conn.commit()

        # 生成导出文件
        os.makedirs(EXPORT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"教师账号_批量生成_{timestamp}.xlsx"
        filepath = os.path.join(EXPORT_DIR, filename)
        df = pd.DataFrame(created, columns=["teacher_id", "teacher_name", "username", "password"])
        df.rename(columns={
            "teacher_id": "教师ID",
            "teacher_name": "教师姓名",
            "username": "账号",
            "password": "初始密码"
        }, inplace=True)
        df.to_excel(filepath, index=False, engine="openpyxl")

        return FileResponse(
            filepath,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    finally:
        conn.close()

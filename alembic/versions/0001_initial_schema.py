"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-30 10:40:00
"""

from __future__ import annotations

import base64
import hashlib
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def _ensure_index(idx_name: str, table_name: str, cols: list[str], unique: bool = False):
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {ix["name"] for ix in inspector.get_indexes(table_name)}
    if idx_name not in existing:
        op.create_index(idx_name, table_name, cols, unique=unique)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "teachers" not in tables:
        op.create_table(
            "teachers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.Text()),
            sa.Column("gender", sa.Text()),
            sa.Column("id_card", sa.Text(), unique=True),
            sa.Column("phone", sa.Text()),
            sa.Column("mobile", sa.Text()),
            sa.Column("short_phone", sa.Text()),
            sa.Column("birth_date", sa.Text()),
            sa.Column("age", sa.Integer()),
            sa.Column("graduate_school", sa.Text()),
            sa.Column("education", sa.Text()),
            sa.Column("political_status", sa.Text()),
            sa.Column("ethnicity", sa.Text()),
            sa.Column("native_place", sa.Text()),
            sa.Column("address", sa.Text()),
            sa.Column("email", sa.Text()),
            sa.Column("title", sa.Text()),
            sa.Column("position", sa.Text()),
            sa.Column("subject", sa.Text()),
            sa.Column("hire_date", sa.Text()),
            sa.Column("employee_id", sa.Text()),
            sa.Column("tags", sa.Text(), server_default="[]"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    if "teacher_extra_fields" not in tables:
        op.create_table(
            "teacher_extra_fields",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("teacher_id", sa.Integer(), nullable=False),
            sa.Column("field_name", sa.Text(), nullable=False),
            sa.Column("field_value", sa.Text()),
            sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("teacher_id", "field_name", name="uq_teacher_extra_field"),
        )

    if "field_registry" not in tables:
        op.create_table(
            "field_registry",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("field_name", sa.Text(), unique=True, nullable=False),
            sa.Column("display_name", sa.Text()),
            sa.Column("field_type", sa.Text(), server_default="TEXT"),
            sa.Column("is_builtin", sa.Integer(), server_default="0"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    if "change_logs" not in tables:
        op.create_table(
            "change_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("teacher_id", sa.Integer()),
            sa.Column("teacher_name", sa.Text()),
            sa.Column("action", sa.Text(), nullable=False),
            sa.Column("field_name", sa.Text()),
            sa.Column("old_value", sa.Text()),
            sa.Column("new_value", sa.Text()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("username", sa.Text(), unique=True, nullable=False),
            sa.Column("password_hash", sa.Text(), nullable=False),
            sa.Column("role", sa.Text(), nullable=False),
            sa.Column("teacher_id", sa.Integer()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="SET NULL"),
        )

    if "user_sessions" not in tables:
        op.create_table(
            "user_sessions",
            sa.Column("token", sa.String(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )

    if "login_rate_limits" not in tables:
        op.create_table(
            "login_rate_limits",
            sa.Column("ip", sa.Text(), primary_key=True),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("window_start_ts", sa.Integer()),
            sa.Column("blocked_until_ts", sa.Integer()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    if "personality_tests" not in tables:
        op.create_table(
            "personality_tests",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("question_ids", sa.Text()),
            sa.Column("answers", sa.Text(), nullable=False),
            sa.Column("answer_items", sa.Text()),
            sa.Column("client_ip", sa.Text()),
            sa.Column("openness", sa.Float(), nullable=False),
            sa.Column("conscientiousness", sa.Float(), nullable=False),
            sa.Column("extraversion", sa.Float(), nullable=False),
            sa.Column("agreeableness", sa.Float(), nullable=False),
            sa.Column("neuroticism", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    else:
        cols = {c["name"] for c in inspector.get_columns("personality_tests")}
        if "question_ids" not in cols:
            op.execute("ALTER TABLE personality_tests ADD COLUMN question_ids TEXT")
        if "answer_items" not in cols:
            op.execute("ALTER TABLE personality_tests ADD COLUMN answer_items TEXT")
        if "client_ip" not in cols:
            op.execute("ALTER TABLE personality_tests ADD COLUMN client_ip TEXT")

    if "teacher_change_requests" not in tables:
        op.create_table(
            "teacher_change_requests",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("teacher_id", sa.Integer(), nullable=False),
            sa.Column("requester_user_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.Text(), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
            sa.Column("reviewer_user_id", sa.Integer()),
            sa.Column("review_note", sa.Text()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("reviewed_at", sa.DateTime()),
            sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="SET NULL"),
        )

    # 索引
    _ensure_index("idx_teachers_name", "teachers", ["name"])
    _ensure_index("idx_teachers_id_card", "teachers", ["id_card"])
    _ensure_index("idx_teachers_mobile", "teachers", ["mobile"])
    _ensure_index("idx_extra_teacher_id", "teacher_extra_fields", ["teacher_id"])
    _ensure_index("idx_logs_teacher_id", "change_logs", ["teacher_id"])
    _ensure_index("idx_users_teacher_id", "users", ["teacher_id"], unique=True)
    _ensure_index("idx_change_requests_status", "teacher_change_requests", ["status"])
    _ensure_index("idx_change_requests_teacher_id", "teacher_change_requests", ["teacher_id"])
    _ensure_index("idx_login_rate_limits_blocked_until", "login_rate_limits", ["blocked_until_ts"])
    _ensure_index("idx_personality_tests_user_id", "personality_tests", ["user_id"])
    _ensure_index("idx_personality_tests_created_at", "personality_tests", ["created_at"])
    _ensure_index("idx_personality_tests_client_ip", "personality_tests", ["client_ip"])

    # 内置字段注册（幂等）
    builtin_fields = [
        ("name", "姓名", "TEXT", 1),
        ("gender", "性别", "TEXT", 1),
        ("id_card", "身份证号", "TEXT", 1),
        ("phone", "联系电话", "TEXT", 1),
        ("mobile", "手机", "TEXT", 1),
        ("short_phone", "小号", "TEXT", 1),
        ("birth_date", "出生日期", "TEXT", 1),
        ("age", "年龄", "INTEGER", 1),
        ("graduate_school", "毕业院校", "TEXT", 1),
        ("education", "学历", "TEXT", 1),
        ("political_status", "政治面貌", "TEXT", 1),
        ("ethnicity", "民族", "TEXT", 1),
        ("native_place", "籍贯", "TEXT", 1),
        ("address", "家庭住址", "TEXT", 1),
        ("email", "邮箱", "TEXT", 1),
        ("title", "职称", "TEXT", 1),
        ("position", "职务", "TEXT", 1),
        ("subject", "任教学科", "TEXT", 1),
        ("hire_date", "入职日期", "TEXT", 1),
        ("employee_id", "工号", "TEXT", 1),
    ]
    for field_name, display_name, field_type, is_builtin in builtin_fields:
        bind.execute(
            text(
                "INSERT OR IGNORE INTO field_registry "
                "(field_name, display_name, field_type, is_builtin) "
                "VALUES (:field_name, :display_name, :field_type, :is_builtin)"
            ),
            {
                "field_name": field_name,
                "display_name": display_name,
                "field_type": field_type,
                "is_builtin": is_builtin,
            },
        )

    # 默认管理员与浏览账号（幂等）
    admin_exists = bind.execute(text("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1")).fetchone()
    if not admin_exists:
        bind.execute(
            text("INSERT INTO users (username, password_hash, role) VALUES (:u, :p, 'admin')"),
            {"u": "admin", "p": _hash_password("admin123")},
        )

    viewer_row = bind.execute(
        text("SELECT id FROM users WHERE role = 'viewer' ORDER BY id LIMIT 1")
    ).fetchone()
    if not viewer_row:
        bind.execute(
            text("INSERT INTO users (username, password_hash, role) VALUES (:u, :p, 'viewer')"),
            {"u": "kan", "p": _hash_password("123")},
        )
    else:
        bind.execute(
            text("UPDATE users SET username = :u, password_hash = :p WHERE id = :id"),
            {"u": "kan", "p": _hash_password("123"), "id": viewer_row[0]},
        )


def downgrade() -> None:
    # 首个迁移不提供自动降级（防止误删生产数据）
    pass

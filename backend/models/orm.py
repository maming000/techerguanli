"""
SQLAlchemy ORM 模型定义（2.0 风格）
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    gender: Mapped[Optional[str]] = mapped_column(Text)
    id_card: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(Text)
    mobile: Mapped[Optional[str]] = mapped_column(Text)
    short_phone: Mapped[Optional[str]] = mapped_column(Text)
    birth_date: Mapped[Optional[str]] = mapped_column(Text)
    age: Mapped[Optional[int]] = mapped_column(Integer)
    graduate_school: Mapped[Optional[str]] = mapped_column(Text)
    education: Mapped[Optional[str]] = mapped_column(Text)
    political_status: Mapped[Optional[str]] = mapped_column(Text)
    ethnicity: Mapped[Optional[str]] = mapped_column(Text)
    native_place: Mapped[Optional[str]] = mapped_column(Text)
    address: Mapped[Optional[str]] = mapped_column(Text)
    email: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    position: Mapped[Optional[str]] = mapped_column(Text)
    subject: Mapped[Optional[str]] = mapped_column(Text)
    hire_date: Mapped[Optional[str]] = mapped_column(Text)
    employee_id: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    extra_fields: Mapped[list["TeacherExtraField"]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan"
    )
    user_account: Mapped[Optional["User"]] = relationship(
        back_populates="teacher", uselist=False
    )


class TeacherExtraField(Base):
    __tablename__ = "teacher_extra_fields"
    __table_args__ = (
        UniqueConstraint("teacher_id", "field_name", name="uq_teacher_extra_field"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    field_value: Mapped[Optional[str]] = mapped_column(Text)

    teacher: Mapped["Teacher"] = relationship(back_populates="extra_fields")


class FieldRegistry(Base):
    __tablename__ = "field_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    field_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(Text)
    field_type: Mapped[Optional[str]] = mapped_column(Text, default="TEXT")
    is_builtin: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class ChangeLog(Base):
    __tablename__ = "change_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[Optional[int]] = mapped_column(Integer)
    teacher_name: Mapped[Optional[str]] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    field_name: Mapped[Optional[str]] = mapped_column(Text)
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    teacher_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teachers.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    teacher: Mapped[Optional["Teacher"]] = relationship(back_populates="user_account")
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    user: Mapped["User"] = relationship(back_populates="sessions")


class LoginRateLimit(Base):
    __tablename__ = "login_rate_limits"

    ip: Mapped[str] = mapped_column(Text, primary_key=True)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    window_start_ts: Mapped[Optional[int]] = mapped_column(Integer)
    blocked_until_ts: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class PersonalityTest(Base):
    __tablename__ = "personality_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    question_ids: Mapped[Optional[str]] = mapped_column(Text)
    answers: Mapped[str] = mapped_column(Text, nullable=False)
    answer_items: Mapped[Optional[str]] = mapped_column(Text)
    client_ip: Mapped[Optional[str]] = mapped_column(Text)
    openness: Mapped[float] = mapped_column(Float, nullable=False)
    conscientiousness: Mapped[float] = mapped_column(Float, nullable=False)
    extraversion: Mapped[float] = mapped_column(Float, nullable=False)
    agreeableness: Mapped[float] = mapped_column(Float, nullable=False)
    neuroticism: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class TeacherChangeRequest(Base):
    __tablename__ = "teacher_change_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False
    )
    requester_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    reviewer_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    review_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

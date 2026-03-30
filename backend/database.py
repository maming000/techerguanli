"""
数据库连接与迁移入口（SQLAlchemy + Alembic）
"""

from __future__ import annotations

import os
from collections.abc import Generator, Iterable
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, CursorResult
from sqlalchemy.orm import Session, sessionmaker

from backend.config import BASE_DIR, DATABASE_DIR, DATABASE_URL


os.makedirs(DATABASE_DIR, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：获取 SQLAlchemy Session。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CompatRow:
    """兼容 sqlite3.Row 的轻量包装。"""

    def __init__(self, raw: Any):
        self._raw = raw
        self._mapping = raw._mapping if hasattr(raw, "_mapping") else raw

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self._raw[key]
        return self._mapping[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._mapping.get(key, default)

    def keys(self) -> list[str]:
        return list(self._mapping.keys())

    def items(self):
        return self._mapping.items()

    def __iter__(self):
        return iter(self._mapping.items())


class CompatCursor:
    """兼容 sqlite cursor API 的轻量包装。"""

    def __init__(self, result: CursorResult[Any]):
        self._result = result
        self.lastrowid = getattr(result, "lastrowid", None)
        self.rowcount = getattr(result, "rowcount", -1)

    def fetchone(self):
        row = self._result.fetchone()
        return CompatRow(row) if row is not None else None

    def fetchall(self):
        return [CompatRow(r) for r in self._result.fetchall()]

    def first(self):
        row = self._result.first()
        return CompatRow(row) if row is not None else None


class CompatConnection:
    """
    兼容层：
    - 允许旧代码继续使用 conn.execute(sql, tuple_params)
    - 底层仍由 SQLAlchemy Engine 管理
    """

    def __init__(self):
        self._conn: Connection = engine.connect()
        self._tx = self._conn.begin()

    @staticmethod
    def _convert_qmark_sql(sql: str, params: Iterable[Any] | dict[str, Any] | None):
        if params is None:
            return sql, {}
        if isinstance(params, dict):
            return sql, params
        p = list(params)
        if not p:
            return sql, {}
        converted = sql
        bind: dict[str, Any] = {}
        for idx, val in enumerate(p):
            name = f"p{idx}"
            converted = converted.replace("?", f":{name}", 1)
            bind[name] = val
        return converted, bind

    def execute(self, sql: str, params: Iterable[Any] | dict[str, Any] | None = None):
        converted_sql, bind = self._convert_qmark_sql(sql, params)
        result = self._conn.execute(text(converted_sql), bind)
        return CompatCursor(result)

    def cursor(self):
        return self

    def commit(self):
        if self._tx.is_active:
            self._tx.commit()
        self._tx = self._conn.begin()

    def rollback(self):
        if self._tx.is_active:
            self._tx.rollback()
        self._tx = self._conn.begin()

    def close(self):
        try:
            if self._tx.is_active:
                self._tx.rollback()
        finally:
            self._conn.close()


def get_connection():
    """
    过渡期兼容接口（非 sqlite3 raw connection）。
    新代码请使用 Depends(get_db)。
    """
    return CompatConnection()


def run_migrations():
    """执行 Alembic 升级到 head。"""
    cfg = Config(os.path.join(BASE_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BASE_DIR, "alembic"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(cfg, "head")


def init_database():
    """初始化入口：统一走 Alembic。"""
    run_migrations()
    print("✅ 数据库迁移完成（Alembic）")

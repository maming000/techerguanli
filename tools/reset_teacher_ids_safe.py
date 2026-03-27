#!/usr/bin/env python3
"""
安全重置教师 ID（保留数据）：
- 自动备份数据库
- 将 teachers.id 重排为连续序号（从 1 开始）
- 同步更新所有关联表中的 teacher_id

使用示例：
  python tools/reset_teacher_ids_safe.py --dry-run
  python tools/reset_teacher_ids_safe.py
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


TABLES_WITH_TEACHER_ID = [
    ("teacher_extra_fields", "teacher_id"),
    ("change_logs", "teacher_id"),
    ("users", "teacher_id"),
    ("teacher_change_requests", "teacher_id"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="安全重置教师 ID（保留数据）")
    parser.add_argument(
        "--db",
        default="database/teachers.db",
        help="SQLite 数据库路径，默认 database/teachers.db",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览，不实际写入",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="不自动备份数据库（不推荐）",
    )
    return parser.parse_args()


def backup_db(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_suffix(db_path.suffix + f".bak_{ts}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def fetch_teacher_ids(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute("SELECT id FROM teachers ORDER BY id ASC").fetchall()
    return [int(r[0]) for r in rows]


def build_mapping(old_ids: list[int]) -> dict[int, int]:
    return {old_id: idx + 1 for idx, old_id in enumerate(old_ids)}


def show_preview(mapping: dict[int, int]):
    old_ids = list(mapping.keys())
    if not old_ids:
        print("teachers 表为空，无需处理。")
        return
    max_old = max(old_ids)
    expected = len(old_ids)
    print(f"教师总数: {expected}")
    print(f"原最大ID: {max_old}")
    print("前 20 条映射(old -> new):")
    for old_id in old_ids[:20]:
        print(f"  {old_id} -> {mapping[old_id]}")
    gap_count = max_old - expected
    if gap_count <= 0:
        print("当前 ID 已连续，无空洞。")
    else:
        print(f"检测到 ID 空洞数量(估算): {gap_count}")


def validate_references(conn: sqlite3.Connection):
    for table, col in TABLES_WITH_TEACHER_ID:
        missing = conn.execute(
            f"SELECT COUNT(*) FROM {table} t "
            f"LEFT JOIN teachers s ON t.{col} = s.id "
            f"WHERE t.{col} IS NOT NULL AND s.id IS NULL"
        ).fetchone()[0]
        if missing:
            raise RuntimeError(f"表 {table}.{col} 存在 {missing} 条无效外键引用")


def reset_ids(conn: sqlite3.Connection, mapping: dict[int, int]):
    if not mapping:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("BEGIN IMMEDIATE")
    try:
        # 第一步：全部转成负数，避免主键冲突
        for old_id in mapping:
            neg_id = -old_id
            conn.execute("UPDATE teachers SET id = ? WHERE id = ?", (neg_id, old_id))
            for table, col in TABLES_WITH_TEACHER_ID:
                conn.execute(
                    f"UPDATE {table} SET {col} = ? WHERE {col} = ?",
                    (neg_id, old_id),
                )

        # 第二步：负数映射到新 ID
        for old_id, new_id in mapping.items():
            neg_id = -old_id
            conn.execute("UPDATE teachers SET id = ? WHERE id = ?", (new_id, neg_id))
            for table, col in TABLES_WITH_TEACHER_ID:
                conn.execute(
                    f"UPDATE {table} SET {col} = ? WHERE {col} = ?",
                    (new_id, neg_id),
                )

        # 重置自增序列
        max_new_id = max(mapping.values())
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'teachers'")
        conn.execute(
            "INSERT INTO sqlite_sequence(name, seq) VALUES('teachers', ?)",
            (max_new_id,),
        )

        validate_references(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def main():
    args = parse_args()
    db_path = Path(args.db).resolve()

    if not db_path.exists():
        raise SystemExit(f"数据库不存在: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        old_ids = fetch_teacher_ids(conn)
        mapping = build_mapping(old_ids)
        show_preview(mapping)

        if args.dry_run:
            print("dry-run 模式：未写入任何改动。")
            return

        if not args.no_backup:
            backup_path = backup_db(db_path)
            print(f"已备份数据库: {backup_path}")

        reset_ids(conn, mapping)
        print("ID 重排完成。")

        new_ids = fetch_teacher_ids(conn)
        if new_ids and (new_ids[0] != 1 or new_ids[-1] != len(new_ids)):
            raise RuntimeError("重排后 ID 非连续，请检查")
        print(f"重排后教师数: {len(new_ids)}，最大ID: {new_ids[-1] if new_ids else 0}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()


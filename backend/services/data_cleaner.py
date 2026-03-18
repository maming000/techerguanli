"""
数据清洗与合并服务
- 去重规则：身份证号 > 手机号 > 姓名
- 合并策略：不覆盖已有数据，仅补全缺失字段
"""
import json
from datetime import datetime
from backend.database import get_connection
from backend.services.id_card_utils import extract_birth_date, calculate_age, extract_gender_from_id
from backend.config import BUILTIN_FIELDS


def clean_value(value) -> str | None:
    """清理字段值"""
    if value is None:
        return None
    val = str(value).strip()
    if val in ("", "nan", "None", "null", "NaN", "N/A", "-", "/"):
        return None
    return val


def clean_phone(phone_str) -> str | None:
    """清理电话号码"""
    val = clean_value(phone_str)
    if not val:
        return None
    # 去除空格、横杠等
    import re
    val = re.sub(r'[\s\-().（）]', '', val)
    # 去除末尾的 .0（pandas 读取数字时可能附带）
    if val.endswith('.0'):
        val = val[:-2]
    return val if val else None


def enrich_from_id_card(record: dict) -> dict:
    """
    从身份证号中自动提取出生日期、年龄、性别
    """
    id_card = record.get("id_card")
    if not id_card:
        return record

    # 提取出生日期
    if not record.get("birth_date"):
        birth_date = extract_birth_date(id_card)
        if birth_date:
            record["birth_date"] = birth_date

    # 计算年龄
    if record.get("birth_date") and not record.get("age"):
        age = calculate_age(record["birth_date"])
        if age is not None:
            record["age"] = age

    # 提取性别
    if not record.get("gender"):
        gender = extract_gender_from_id(id_card)
        if gender:
            record["gender"] = gender

    return record


def find_existing_teacher(conn, record: dict) -> dict | None:
    """
    按优先级查找已存在的教师记录
    优先级：身份证号 > 手机号 > 姓名
    """
    # 1. 身份证号匹配
    id_card = record.get("id_card")
    if id_card:
        row = conn.execute("SELECT * FROM teachers WHERE id_card = ?", (id_card,)).fetchone()
        if row:
            return dict(row)

    # 2. 手机号匹配
    mobile = record.get("mobile")
    if mobile:
        row = conn.execute("SELECT * FROM teachers WHERE mobile = ?", (mobile,)).fetchone()
        if row:
            return dict(row)

    # 3. 姓名匹配（仅在有姓名时）
    name = record.get("name")
    if name:
        row = conn.execute("SELECT * FROM teachers WHERE name = ?", (name,)).fetchone()
        if row:
            return dict(row)

    return None


def merge_teacher(conn, existing: dict, new_data: dict, extra_fields: dict = None) -> tuple[bool, list]:
    """
    合并教师数据：不覆盖已有数据，仅补全缺失字段
    返回: (是否有更新, 变更日志列表)
    """
    changes = []
    update_fields = {}
    teacher_id = existing["id"]
    teacher_name = existing.get("name") or new_data.get("name") or "未知"

    # 合并主表字段
    for field in BUILTIN_FIELDS:
        if field == "tags":
            continue
        new_val = new_data.get(field)
        old_val = existing.get(field)
        if new_val and not old_val:
            update_fields[field] = new_val
            changes.append({
                "teacher_id": teacher_id,
                "teacher_name": teacher_name,
                "action": "补全字段",
                "field_name": field,
                "old_value": None,
                "new_value": str(new_val)
            })

    # 更新主表
    if update_fields:
        update_fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        set_clause = ", ".join(f"{k} = ?" for k in update_fields)
        values = list(update_fields.values()) + [teacher_id]
        conn.execute(f"UPDATE teachers SET {set_clause} WHERE id = ?", values)

    # 合并扩展字段
    if extra_fields:
        for field_name, field_value in extra_fields.items():
            if not field_value:
                continue
            existing_extra = conn.execute(
                "SELECT field_value FROM teacher_extra_fields WHERE teacher_id = ? AND field_name = ?",
                (teacher_id, field_name)
            ).fetchone()
            if not existing_extra:
                conn.execute(
                    "INSERT INTO teacher_extra_fields (teacher_id, field_name, field_value) VALUES (?, ?, ?)",
                    (teacher_id, field_name, field_value)
                )
                changes.append({
                    "teacher_id": teacher_id,
                    "teacher_name": teacher_name,
                    "action": "补全扩展字段",
                    "field_name": field_name,
                    "old_value": None,
                    "new_value": str(field_value)
                })

    # 记录变更日志
    for change in changes:
        conn.execute(
            "INSERT INTO change_logs (teacher_id, teacher_name, action, field_name, old_value, new_value) VALUES (?, ?, ?, ?, ?, ?)",
            (change["teacher_id"], change["teacher_name"], change["action"],
             change["field_name"], change["old_value"], change["new_value"])
        )

    return len(changes) > 0, changes


def insert_teacher(conn, record: dict, extra_fields: dict = None) -> int:
    """
    插入新教师记录
    返回新记录的 ID
    """
    # 准备主表数据
    main_fields = {}
    for field in BUILTIN_FIELDS:
        if field == "tags":
            main_fields["tags"] = json.dumps(record.get("tags", []), ensure_ascii=False)
        elif field in record and record[field] is not None:
            main_fields[field] = record[field]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    main_fields["created_at"] = now
    main_fields["updated_at"] = now

    columns = ", ".join(main_fields.keys())
    placeholders = ", ".join("?" * len(main_fields))
    values = list(main_fields.values())

    cursor = conn.execute(
        f"INSERT INTO teachers ({columns}) VALUES ({placeholders})", values
    )
    teacher_id = cursor.lastrowid

    # 插入扩展字段
    if extra_fields:
        for field_name, field_value in extra_fields.items():
            if field_value:
                conn.execute(
                    "INSERT INTO teacher_extra_fields (teacher_id, field_name, field_value) VALUES (?, ?, ?)",
                    (teacher_id, field_name, str(field_value))
                )

    # 记录日志
    teacher_name = record.get("name", "未知")
    conn.execute(
        "INSERT INTO change_logs (teacher_id, teacher_name, action, field_name, old_value, new_value) VALUES (?, ?, '新增教师', NULL, NULL, NULL)",
        (teacher_id, teacher_name)
    )

    return teacher_id


def process_records(records: list[dict]) -> dict:
    """
    处理一批教师记录：清洗、去重、合并或插入
    返回处理结果统计
    """
    conn = get_connection()
    stats = {"new": 0, "updated": 0, "skipped": 0, "errors": []}

    try:
        for record in records:
            try:
                # 清洗数据
                cleaned = {}
                extra = {}
                for key, value in record.items():
                    if key in BUILTIN_FIELDS:
                        if key in ("phone", "mobile", "short_phone"):
                            cleaned[key] = clean_phone(value)
                        elif key == "tags":
                            cleaned[key] = value if isinstance(value, list) else []
                        elif key == "age":
                            try:
                                cleaned[key] = int(float(str(value))) if value else None
                            except (ValueError, TypeError):
                                cleaned[key] = None
                        else:
                            cleaned[key] = clean_value(value)
                    else:
                        val = clean_value(value)
                        if val:
                            extra[key] = val

                # 清理身份证号中的空格
                if cleaned.get("id_card"):
                    cleaned["id_card"] = cleaned["id_card"].replace(" ", "")

                # 从身份证号提取信息
                cleaned = enrich_from_id_card(cleaned)

                # 查找已存在记录
                existing = find_existing_teacher(conn, cleaned)

                if existing:
                    updated, _ = merge_teacher(conn, existing, cleaned, extra)
                    if updated:
                        stats["updated"] += 1
                    else:
                        stats["skipped"] += 1
                else:
                    insert_teacher(conn, cleaned, extra)
                    stats["new"] += 1

            except Exception as e:
                name = record.get("name", "未知")
                stats["errors"].append(f"处理 {name} 时出错: {str(e)}")

        conn.commit()
    except Exception as e:
        conn.rollback()
        stats["errors"].append(f"批量处理失败: {str(e)}")
    finally:
        conn.close()

    return stats

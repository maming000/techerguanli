"""
教师管理路由 - CRUD + 查询 + 标签
"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend.database import get_connection
from backend.models import (
    TeacherCreate, TeacherUpdate, TeacherResponse,
    TeacherListResponse, ChangeLogResponse
)
from backend.config import BUILTIN_FIELDS
from backend.services.id_card_utils import calculate_age, extract_birth_date, validate_id_card

router = APIRouter(prefix="/api/teachers", tags=["教师管理"])


def row_to_teacher_response(row: dict, conn) -> TeacherResponse:
    """将数据库行转换为响应模型"""
    # 获取扩展字段
    extras = conn.execute(
        "SELECT field_name, field_value FROM teacher_extra_fields WHERE teacher_id = ?",
        (row["id"],)
    ).fetchall()
    extra_fields = {e["field_name"]: e["field_value"] for e in extras}

    # 解析标签
    tags = []
    if row.get("tags"):
        try:
            tags = json.loads(row["tags"])
        except (json.JSONDecodeError, TypeError):
            tags = []

    # 动态计算年龄：优先使用身份证号推导出生日期与年龄
    age = row.get("age")
    birth_date = row.get("birth_date")
    id_card = row.get("id_card")
    if id_card and validate_id_card(id_card):
        derived_birth = extract_birth_date(id_card)
        if derived_birth:
            birth_date = derived_birth
            computed_age = calculate_age(derived_birth)
            if computed_age is not None:
                age = computed_age
    elif birth_date:
        computed_age = calculate_age(birth_date)
        if computed_age is not None:
            age = computed_age

    return TeacherResponse(
        id=row["id"],
        name=row.get("name"),
        gender=row.get("gender"),
        id_card=row.get("id_card"),
        phone=row.get("phone"),
        mobile=row.get("mobile"),
        short_phone=row.get("short_phone"),
        birth_date=birth_date,
        age=age,
        graduate_school=row.get("graduate_school"),
        education=row.get("education"),
        political_status=row.get("political_status"),
        ethnicity=row.get("ethnicity"),
        native_place=row.get("native_place"),
        address=row.get("address"),
        email=row.get("email"),
        title=row.get("title"),
        position=row.get("position"),
        subject=row.get("subject"),
        hire_date=row.get("hire_date"),
        employee_id=row.get("employee_id"),
        tags=tags,
        extra_fields=extra_fields,
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at")
    )


@router.get("/", response_model=TeacherListResponse)
async def list_teachers(
    keyword: Optional[str] = Query(None, description="搜索关键词（姓名/电话模糊搜索）"),
    gender: Optional[str] = Query(None, description="性别筛选"),
    phone: Optional[str] = Query(None, description="电话筛选（手机/座机/短号）"),
    birth_date: Optional[str] = Query(None, description="出生日期筛选（YYYY-MM-DD）"),
    political_status: Optional[str] = Query(None, description="政治面貌"),
    education: Optional[str] = Query(None, description="学历"),
    title: Optional[str] = Query(None, description="职称"),
    original_unit: Optional[str] = Query(None, description="原单位"),
    public_service_time: Optional[str] = Query(None, description="参公时间"),
    car_plate: Optional[str] = Query(None, description="车牌号码"),
    graduate_school: Optional[str] = Query(None, description="毕业院校"),
    ethnicity: Optional[str] = Query(None, description="民族"),
    address: Optional[str] = Query(None, description="家庭住址"),
    min_age: Optional[int] = Query(None, description="最小年龄"),
    max_age: Optional[int] = Query(None, description="最大年龄"),
    tag: Optional[str] = Query(None, description="标签筛选"),
    subject: Optional[str] = Query(None, description="学科"),
    hire_date: Optional[str] = Query(None, description="入职时间"),
    sort_by: Optional[str] = Query(None, description="排序字段: name/age/gender/education/hire_date/subject/id"),
    sort_order: Optional[str] = Query("asc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数")
):
    """查询教师列表（分页 + 多条件筛选 + 排序）"""
    conn = get_connection()
    try:
        conditions = []
        params = []

        extra_field_aliases = {
            "original_unit": ["原单位", "原工作单位", "original_unit"],
            "public_service_time": ["参公时间", "参公日期", "public_service_time"],
            "car_plate": ["车牌号码", "车牌号", "车牌", "car_plate", "car_plate_number"],
        }

        def add_extra_like(aliases: list[str], value: str, name_like: str | None = None):
            placeholders = ", ".join("?" * len(aliases)) if aliases else ""
            name_conditions = []
            if aliases:
                name_conditions.append(f"tef.field_name IN ({placeholders})")
            if name_like:
                name_conditions.append("tef.field_name LIKE ?")
            name_clause = " OR ".join(name_conditions) if name_conditions else "1=1"
            conditions.append(
                f"EXISTS (SELECT 1 FROM teacher_extra_fields tef "
                f"WHERE tef.teacher_id = teachers.id AND ({name_clause}) "
                f"AND lower(tef.field_value) LIKE lower(?))"
            )
            if aliases:
                params.extend(aliases)
            if name_like:
                params.append(name_like)
            params.append(f"%{value}%")

        if keyword:
            conditions.append("(name LIKE ? OR phone LIKE ? OR mobile LIKE ? OR id_card LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw, kw])

        if gender:
            conditions.append("gender LIKE ?")
            params.append(f"%{gender}%")

        if phone:
            conditions.append("(phone LIKE ? OR mobile LIKE ? OR short_phone LIKE ?)")
            ph = f"%{phone}%"
            params.extend([ph, ph, ph])

        if birth_date:
            conditions.append("birth_date LIKE ?")
            params.append(f"%{birth_date}%")

        if political_status:
            conditions.append("political_status = ?")
            params.append(political_status)

        if education:
            conditions.append("education LIKE ?")
            params.append(f"%{education}%")

        if title:
            conditions.append("title LIKE ?")
            params.append(f"%{title}%")

        if graduate_school:
            conditions.append("graduate_school LIKE ?")
            params.append(f"%{graduate_school}%")

        if ethnicity:
            conditions.append("ethnicity LIKE ?")
            params.append(f"%{ethnicity}%")

        if address:
            conditions.append("address LIKE ?")
            params.append(f"%{address}%")

        # 年龄筛选：优先按出生日期/身份证号动态计算，回退到存储的 age
        derived_birth = (
            "CASE "
            "WHEN id_card IS NOT NULL AND length(id_card)=18 THEN "
            "substr(id_card,7,4)||'-'||substr(id_card,11,2)||'-'||substr(id_card,13,2) "
            "WHEN id_card IS NOT NULL AND length(id_card)=15 THEN "
            "'19'||substr(id_card,7,2)||'-'||substr(id_card,9,2)||'-'||substr(id_card,11,2) "
            "END"
        )
        normalized_birth = (
            "CASE "
            "WHEN birth_date IS NOT NULL AND length(trim(birth_date)) >= 10 THEN "
            "replace(replace(substr(trim(birth_date),1,10), '/', '-'), '.', '-') "
            "WHEN birth_date IS NOT NULL AND length(trim(birth_date)) = 8 "
            "AND trim(birth_date) GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]' THEN "
            "substr(trim(birth_date),1,4)||'-'||substr(trim(birth_date),5,2)||'-'||substr(trim(birth_date),7,2) "
            "END"
        )
        birth_expr = f"COALESCE({normalized_birth}, {derived_birth})"
        computed_age = (
            f"(CAST(strftime('%Y','now') AS INTEGER) - CAST(strftime('%Y', {birth_expr}) AS INTEGER) - "
            f"(strftime('%m-%d','now') < strftime('%m-%d', {birth_expr})))"
        )
        age_expr = f"COALESCE({computed_age}, age)"

        if min_age is not None:
            conditions.append(f"{age_expr} >= ?")
            params.append(min_age)

        if max_age is not None:
            conditions.append(f"{age_expr} <= ?")
            params.append(max_age)

        if tag:
            conditions.append("tags LIKE ?")
            params.append(f'%"{tag}"%')

        if subject:
            conditions.append("subject LIKE ?")
            params.append(f"%{subject}%")

        if hire_date:
            conditions.append("hire_date LIKE ?")
            params.append(f"%{hire_date}%")

        if original_unit:
            add_extra_like(extra_field_aliases["original_unit"], original_unit)

        if public_service_time:
            add_extra_like(extra_field_aliases["public_service_time"], public_service_time)

        if car_plate:
            add_extra_like(extra_field_aliases["car_plate"], car_plate, "%车牌%")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 排序
        allowed_sort_fields = {"name", "age", "gender", "education", "political_status", "hire_date", "subject", "id", "created_at"}
        order_dir = "DESC" if sort_order and sort_order.lower() == "desc" else "ASC"
        if sort_by and sort_by in allowed_sort_fields:
            # NULL 值排到最后
            order_clause = f"{sort_by} IS NULL, {sort_by} {order_dir}"
        else:
            order_clause = "id ASC"

        # 统计总数
        total = conn.execute(
            f"SELECT COUNT(*) FROM teachers WHERE {where_clause}", params
        ).fetchone()[0]

        # 分页查询
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT * FROM teachers WHERE {where_clause} ORDER BY {order_clause} LIMIT ? OFFSET ?",
            params + [page_size, offset]
        ).fetchall()

        teachers = [row_to_teacher_response(dict(row), conn) for row in rows]

        total_pages = (total + page_size - 1) // page_size

        return TeacherListResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            data=teachers
        )
    finally:
        conn.close()


@router.get("/{teacher_id}", response_model=TeacherResponse)
async def get_teacher(teacher_id: int):
    """获取教师详情"""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="教师不存在")
        return row_to_teacher_response(dict(row), conn)
    finally:
        conn.close()


@router.put("/{teacher_id}", response_model=TeacherResponse)
async def update_teacher(teacher_id: int, data: TeacherUpdate):
    """更新教师信息"""
    conn = get_connection()
    try:
        existing = conn.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="教师不存在")

        existing = dict(existing)
        update_data = data.model_dump(exclude_none=True, exclude={"extra_fields"})

        # 记录变更日志
        changes = []
        for field, new_val in list(update_data.items()):
            if field == "tags":
                new_val_str = json.dumps(new_val, ensure_ascii=False)
                old_val = existing.get(field, "[]")
                # 无论是否变更，都必须将 list 转为 JSON 字符串
                update_data[field] = new_val_str
                if new_val_str != old_val:
                    changes.append((field, old_val, new_val_str))
            else:
                old_val = existing.get(field)
                if str(new_val) != str(old_val):
                    changes.append((field, old_val, new_val))

        # 更新主表
        if update_data:
            update_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            set_clause = ", ".join(f"{k} = ?" for k in update_data)
            values = list(update_data.values()) + [teacher_id]
            conn.execute(f"UPDATE teachers SET {set_clause} WHERE id = ?", values)

        # 更新扩展字段
        if data.extra_fields:
            for field_name, field_value in data.extra_fields.items():
                old = conn.execute(
                    "SELECT field_value FROM teacher_extra_fields WHERE teacher_id = ? AND field_name = ?",
                    (teacher_id, field_name)
                ).fetchone()
                old_val = old["field_value"] if old else None

                if old:
                    conn.execute(
                        "UPDATE teacher_extra_fields SET field_value = ? WHERE teacher_id = ? AND field_name = ?",
                        (field_value, teacher_id, field_name)
                    )
                else:
                    conn.execute(
                        "INSERT INTO teacher_extra_fields (teacher_id, field_name, field_value) VALUES (?, ?, ?)",
                        (teacher_id, field_name, field_value)
                    )
                if str(field_value) != str(old_val):
                    changes.append((field_name, old_val, field_value))

        # 保存变更日志
        teacher_name = existing.get("name") or data.name or "未知"
        for field_name, old_val, new_val in changes:
            conn.execute(
                "INSERT INTO change_logs (teacher_id, teacher_name, action, field_name, old_value, new_value) VALUES (?, ?, '修改', ?, ?, ?)",
                (teacher_id, teacher_name, field_name, str(old_val) if old_val else None, str(new_val))
            )

        conn.commit()

        # 返回更新后的数据
        row = conn.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
        return row_to_teacher_response(dict(row), conn)
    finally:
        conn.close()


@router.delete("/{teacher_id}")
async def delete_teacher(teacher_id: int):
    """删除教师"""
    conn = get_connection()
    try:
        existing = conn.execute("SELECT name FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="教师不存在")

        conn.execute("DELETE FROM teacher_extra_fields WHERE teacher_id = ?", (teacher_id,))
        conn.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))

        # 记录日志
        conn.execute(
            "INSERT INTO change_logs (teacher_id, teacher_name, action) VALUES (?, ?, '删除教师')",
            (teacher_id, existing["name"])
        )
        conn.commit()
        return {"message": "删除成功"}
    finally:
        conn.close()


@router.post("/{teacher_id}/tags")
async def add_tag(teacher_id: int, tag: str = Query(..., description="标签名称")):
    """添加标签"""
    conn = get_connection()
    try:
        row = conn.execute("SELECT tags, name FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="教师不存在")

        tags = json.loads(row["tags"] or "[]")
        if tag not in tags:
            tags.append(tag)
            conn.execute(
                "UPDATE teachers SET tags = ?, updated_at = ? WHERE id = ?",
                (json.dumps(tags, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), teacher_id)
            )
            conn.execute(
                "INSERT INTO change_logs (teacher_id, teacher_name, action, field_name, new_value) VALUES (?, ?, '添加标签', 'tags', ?)",
                (teacher_id, row["name"], tag)
            )
            conn.commit()

        return {"tags": tags}
    finally:
        conn.close()


@router.delete("/{teacher_id}/tags")
async def remove_tag(teacher_id: int, tag: str = Query(..., description="标签名称")):
    """删除标签"""
    conn = get_connection()
    try:
        row = conn.execute("SELECT tags, name FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="教师不存在")

        tags = json.loads(row["tags"] or "[]")
        if tag in tags:
            tags.remove(tag)
            conn.execute(
                "UPDATE teachers SET tags = ?, updated_at = ? WHERE id = ?",
                (json.dumps(tags, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), teacher_id)
            )
            conn.execute(
                "INSERT INTO change_logs (teacher_id, teacher_name, action, field_name, old_value) VALUES (?, ?, '删除标签', 'tags', ?)",
                (teacher_id, row["name"], tag)
            )
            conn.commit()

        return {"tags": tags}
    finally:
        conn.close()


@router.get("/{teacher_id}/logs", response_model=list[ChangeLogResponse])
async def get_teacher_logs(teacher_id: int):
    """获取教师修改记录"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM change_logs WHERE teacher_id = ? ORDER BY created_at DESC LIMIT 100",
            (teacher_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.post("/batch-update")
async def batch_update(teacher_ids: list[int], field: str, value: str):
    """批量修改教师字段"""
    conn = get_connection()
    try:
        updated = 0
        for tid in teacher_ids:
            row = conn.execute("SELECT * FROM teachers WHERE id = ?", (tid,)).fetchone()
            if not row:
                continue
            row = dict(row)

            if field in BUILTIN_FIELDS:
                old_val = row.get(field)
                if field == "tags":
                    # 对标签做追加
                    tags = json.loads(row.get("tags") or "[]")
                    if value not in tags:
                        tags.append(value)
                    new_val = json.dumps(tags, ensure_ascii=False)
                else:
                    new_val = value

                conn.execute(
                    f"UPDATE teachers SET {field} = ?, updated_at = ? WHERE id = ?",
                    (new_val, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tid)
                )
            else:
                old_extra = conn.execute(
                    "SELECT field_value FROM teacher_extra_fields WHERE teacher_id = ? AND field_name = ?",
                    (tid, field)
                ).fetchone()
                old_val = old_extra["field_value"] if old_extra else None

                if old_extra:
                    conn.execute(
                        "UPDATE teacher_extra_fields SET field_value = ? WHERE teacher_id = ? AND field_name = ?",
                        (value, tid, field)
                    )
                else:
                    conn.execute(
                        "INSERT INTO teacher_extra_fields (teacher_id, field_name, field_value) VALUES (?, ?, ?)",
                        (tid, field, value)
                    )

            conn.execute(
                "INSERT INTO change_logs (teacher_id, teacher_name, action, field_name, old_value, new_value) VALUES (?, ?, '批量修改', ?, ?, ?)",
                (tid, row.get("name", "未知"), field, str(old_val) if old_val else None, value)
            )
            updated += 1

        conn.commit()
        return {"updated": updated}
    finally:
        conn.close()

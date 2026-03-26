"""
教师管理路由 - CRUD + 查询 + 标签
"""
import json
import os
import re
import secrets
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File, Form
from typing import Optional, Any
from backend.database import get_connection
from backend.models import (
    TeacherCreate, TeacherUpdate, TeacherResponse,
    TeacherListResponse, ChangeLogResponse
)
from backend.config import BUILTIN_FIELDS, FIELD_MAPPING, UPLOAD_DIR
from backend.services.id_card_utils import calculate_age, extract_birth_date, validate_id_card
from backend.services.auth_utils import get_current_user, require_admin
from backend.services.field_detector import normalize_field_name
from backend.services.data_cleaner import (
    MERGE_POLICIES,
    normalize_record,
    find_existing_teacher_with_reason,
    merge_teacher,
    insert_teacher,
)
from backend.services.auth_utils import hash_password, validate_password_strength
from backend.config import TEACHER_ONBOARDING_CODE

router = APIRouter(prefix="/api/teachers", tags=["教师管理"])
AVATAR_DIR = os.path.join(UPLOAD_DIR, "avatars")


def _safe_ext(filename: str) -> str:
    ext = os.path.splitext((filename or "").lower())[1]
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        return ext
    return ""


def _normalize_cover_color(color: str | None) -> str:
    if not color:
        return ""
    c = color.strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", c):
        return c.lower()
    return ""


def _normalize_id_card_value(id_card: str | None) -> str:
    if not id_card:
        return ""
    return str(id_card).strip().replace(" ", "").upper()


def _validate_and_normalize_id_card(id_card: str | None):
    val = _normalize_id_card_value(id_card)
    if not val:
        return
    if not validate_id_card(val):
        raise HTTPException(status_code=400, detail="身份证号格式或校验位不正确")
    if not extract_birth_date(val):
        raise HTTPException(status_code=400, detail="身份证号中的出生日期无效")


def _build_teacher_username(conn, teacher_id: int) -> str:
    base = f"t{teacher_id}"
    username = base
    suffix = 1
    while conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        username = f"{base}{suffix}"
        suffix += 1
    return username


def _generate_initial_password() -> str:
    # 生成可读性较好的随机密码
    pwd = secrets.token_urlsafe(8)
    validate_password_strength(pwd)
    return pwd


def _create_or_reset_teacher_account(conn, teacher_id: int) -> tuple[str, str]:
    row = conn.execute(
        "SELECT id, username FROM users WHERE teacher_id = ? AND role = 'teacher'",
        (teacher_id,)
    ).fetchone()
    password = _generate_initial_password()
    pwd_hash = hash_password(password)

    if row:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (pwd_hash, row["id"])
        )
        return row["username"], password

    username = _build_teacher_username(conn, teacher_id)
    conn.execute(
        "INSERT INTO users (username, password_hash, role, teacher_id) VALUES (?, ?, 'teacher', ?)",
        (username, pwd_hash, teacher_id)
    )
    return username, password


def _create_change_request(conn, teacher_id: int, requester_user_id: int, action: str, payload: dict) -> int:
    cursor = conn.execute(
        "INSERT INTO teacher_change_requests (teacher_id, requester_user_id, action, payload_json, status) VALUES (?, ?, ?, ?, 'pending')",
        (teacher_id, requester_user_id, action, json.dumps(payload, ensure_ascii=False))
    )
    return int(cursor.lastrowid)


def _apply_teacher_update(conn, teacher_id: int, payload: dict) -> dict:
    existing = conn.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="教师不存在")

    existing = dict(existing)
    update_data = (payload.get("update_data") or {}).copy()
    extra_fields = payload.get("extra_fields")

    for k, v in list(update_data.items()):
        if isinstance(v, str) and v.strip() == "":
            update_data[k] = None

    changes = []
    for field, new_val in list(update_data.items()):
        if field == "tags":
            new_val_str = json.dumps(new_val, ensure_ascii=False)
            old_val = existing.get(field, "[]")
            update_data[field] = new_val_str
            if new_val_str != old_val:
                changes.append((field, old_val, new_val_str))
        else:
            old_val = existing.get(field)
            if str(new_val) != str(old_val):
                changes.append((field, old_val, new_val))

    if update_data:
        update_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        set_clause = ", ".join(f"{k} = ?" for k in update_data)
        values = list(update_data.values()) + [teacher_id]
        conn.execute(f"UPDATE teachers SET {set_clause} WHERE id = ?", values)

    if extra_fields is not None:
        for field_name, field_value in extra_fields.items():
            norm = normalize_field_name(field_name)
            builtin_field = None
            if norm in FIELD_MAPPING:
                builtin_field = FIELD_MAPPING[norm]
            elif norm in BUILTIN_FIELDS:
                builtin_field = norm

            if builtin_field:
                continue

            old = conn.execute(
                "SELECT field_value FROM teacher_extra_fields WHERE teacher_id = ? AND field_name = ?",
                (teacher_id, field_name)
            ).fetchone()
            old_val = old["field_value"] if old else None

            is_empty = field_value is None or (isinstance(field_value, str) and field_value.strip() == "")
            if is_empty:
                if old:
                    conn.execute(
                        "DELETE FROM teacher_extra_fields WHERE teacher_id = ? AND field_name = ?",
                        (teacher_id, field_name)
                    )
                    changes.append((field_name, old_val, None))
            else:
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

    teacher_name = existing.get("name") or "未知"
    for field_name, old_val, new_val in changes:
        conn.execute(
            "INSERT INTO change_logs (teacher_id, teacher_name, action, field_name, old_value, new_value) VALUES (?, ?, '修改', ?, ?, ?)",
            (teacher_id, teacher_name, field_name, str(old_val) if old_val else None, str(new_val))
        )

    row = conn.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
    return dict(row)


def _apply_tag_change(conn, teacher_id: int, tag: str, mode: str):
    row = conn.execute("SELECT tags, name FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="教师不存在")

    tags = json.loads(row["tags"] or "[]")
    if mode == "add":
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
    else:
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
    return tags


def _apply_profile_theme(conn, teacher_id: int, cover_color: str):
    row = conn.execute("SELECT name FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="教师不存在")

    old_row = conn.execute(
        "SELECT field_value FROM teacher_extra_fields WHERE teacher_id = ? AND field_name = ?",
        (teacher_id, "__profile_cover_color")
    ).fetchone()
    old_color = old_row["field_value"] if old_row else None

    if old_row:
        conn.execute(
            "UPDATE teacher_extra_fields SET field_value = ? WHERE teacher_id = ? AND field_name = ?",
            (cover_color, teacher_id, "__profile_cover_color")
        )
    else:
        conn.execute(
            "INSERT INTO teacher_extra_fields (teacher_id, field_name, field_value) VALUES (?, ?, ?)",
            (teacher_id, "__profile_cover_color", cover_color)
        )

    if old_color != cover_color:
        conn.execute(
            "INSERT INTO change_logs (teacher_id, teacher_name, action, field_name, old_value, new_value) VALUES (?, ?, '修改', ?, ?, ?)",
            (teacher_id, row["name"], "__profile_cover_color", old_color, cover_color)
        )
    conn.execute(
        "UPDATE teachers SET updated_at = ? WHERE id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), teacher_id)
    )


def _apply_avatar_update(conn, teacher_id: int, avatar_url: str, cover_color: str = ""):
    row = conn.execute("SELECT name FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="教师不存在")

    old_avatar_row = conn.execute(
        "SELECT field_value FROM teacher_extra_fields WHERE teacher_id = ? AND field_name = ?",
        (teacher_id, "__profile_avatar")
    ).fetchone()
    old_avatar = old_avatar_row["field_value"] if old_avatar_row else None

    if old_avatar_row:
        conn.execute(
            "UPDATE teacher_extra_fields SET field_value = ? WHERE teacher_id = ? AND field_name = ?",
            (avatar_url, teacher_id, "__profile_avatar")
        )
    else:
        conn.execute(
            "INSERT INTO teacher_extra_fields (teacher_id, field_name, field_value) VALUES (?, ?, ?)",
            (teacher_id, "__profile_avatar", avatar_url)
        )

    if old_avatar and old_avatar != avatar_url and old_avatar.startswith("/uploads/avatars/"):
        old_file = os.path.join(UPLOAD_DIR, old_avatar.replace("/uploads/", "", 1))
        try:
            if os.path.exists(old_file):
                os.remove(old_file)
        except OSError:
            pass

    conn.execute(
        "INSERT INTO change_logs (teacher_id, teacher_name, action, field_name, old_value, new_value) VALUES (?, ?, '修改', ?, ?, ?)",
        (teacher_id, row["name"], "__profile_avatar", old_avatar, avatar_url)
    )

    if cover_color:
        _apply_profile_theme(conn, teacher_id, cover_color)
    else:
        conn.execute(
            "UPDATE teachers SET updated_at = ? WHERE id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), teacher_id)
        )


def _apply_change_request(conn, request_row: dict):
    action = request_row["action"]
    payload = json.loads(request_row["payload_json"] or "{}")
    teacher_id = request_row["teacher_id"]

    if action == "update_teacher":
        _apply_teacher_update(conn, teacher_id, payload)
    elif action == "add_tag":
        _apply_tag_change(conn, teacher_id, payload.get("tag", ""), "add")
    elif action == "remove_tag":
        _apply_tag_change(conn, teacher_id, payload.get("tag", ""), "remove")
    elif action == "update_avatar":
        _apply_avatar_update(conn, teacher_id, payload.get("avatar_url", ""), payload.get("cover_color", ""))
    elif action == "update_theme":
        _apply_profile_theme(conn, teacher_id, payload.get("cover_color", ""))
    else:
        raise HTTPException(status_code=400, detail=f"未知审核动作: {action}")


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
        account_username=row.get("account_username"),
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
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    user: dict = Depends(get_current_user)
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
                f"WHERE tef.teacher_id = t.id AND ({name_clause}) "
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

        # 教师账号只能查看自己的信息
        if user.get("role") == "teacher":
            teacher_id = user.get("teacher_id")
            if not teacher_id:
                raise HTTPException(status_code=403, detail="账号未绑定教师")
            conditions.append("t.id = ?")
            params.append(teacher_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 排序
        allowed_sort_fields = {"name", "age", "gender", "education", "political_status", "hire_date", "subject", "id", "created_at"}
        order_dir = "DESC" if sort_order and sort_order.lower() == "desc" else "ASC"
        if sort_by and sort_by in allowed_sort_fields:
            # NULL 值排到最后
            order_field = f"t.{sort_by}"
            order_clause = f"{order_field} IS NULL, {order_field} {order_dir}"
        else:
            order_clause = "t.id ASC"

        # 统计总数
        total = conn.execute(
            f"SELECT COUNT(*) FROM teachers t LEFT JOIN users u ON u.teacher_id = t.id WHERE {where_clause}",
            params
        ).fetchone()[0]

        # 分页查询
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT t.*, u.username as account_username "
            f"FROM teachers t LEFT JOIN users u ON u.teacher_id = t.id "
            f"WHERE {where_clause} ORDER BY {order_clause} LIMIT ? OFFSET ?",
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
async def get_teacher(teacher_id: int, user: dict = Depends(get_current_user)):
    """获取教师详情"""
    if user.get("role") == "teacher" and user.get("teacher_id") != teacher_id:
        raise HTTPException(status_code=403, detail="无权限")
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT t.*, u.username as account_username "
            "FROM teachers t LEFT JOIN users u ON u.teacher_id = t.id "
            "WHERE t.id = ?",
            (teacher_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="教师不存在")
        return row_to_teacher_response(dict(row), conn)
    finally:
        conn.close()


@router.post("/questionnaire")
async def create_or_merge_teacher_by_questionnaire(
    data: TeacherCreate,
    merge_policy: str = Query("fill_missing", description="fill_missing/overwrite/skip_existing"),
    user: dict = Depends(get_current_user)
):
    """问卷式录入：按规则去重后新增或合并"""
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="浏览账号不允许修改")

    policy = (merge_policy or "fill_missing").strip()
    if policy not in MERGE_POLICIES:
        raise HTTPException(status_code=400, detail=f"不支持的合并策略: {policy}")

    payload = data.model_dump(exclude_none=True)
    if "id_card" in payload:
        payload["id_card"] = _normalize_id_card_value(payload.get("id_card"))
        _validate_and_normalize_id_card(payload.get("id_card"))
    extra_fields = payload.pop("extra_fields", {}) or {}
    source_record = {**payload, **extra_fields}
    cleaned, extra = normalize_record(source_record)

    if not cleaned.get("name"):
        raise HTTPException(status_code=400, detail="姓名为必填项")

    conn = get_connection()
    try:
        existing, matched_by = find_existing_teacher_with_reason(conn, cleaned)
        if existing:
            updated, _ = merge_teacher(conn, existing, cleaned, extra, merge_policy=policy)
            conn.commit()
            return {
                "action": "updated" if updated else "skipped",
                "teacher_id": existing["id"],
                "matched_by": matched_by,
                "merge_policy": policy,
                "message": "匹配到重复教师，已更新" if updated else "匹配到重复教师，无需变更"
            }

        teacher_id = insert_teacher(conn, cleaned, extra)
        conn.commit()
        return {
            "action": "created",
            "teacher_id": teacher_id,
            "matched_by": None,
            "merge_policy": policy,
            "message": "问卷录入成功，已新增教师"
        }
    finally:
        conn.close()


@router.post("/public/onboard")
async def public_teacher_onboard(
    data: TeacherCreate,
    code: str = Query("", description="公开入职口令")
):
    """公开新教师自助录入：去重建档并返回账号密码"""
    if not TEACHER_ONBOARDING_CODE:
        raise HTTPException(status_code=503, detail="系统未配置入职口令，请联系管理员")
    if (code or "").strip() != TEACHER_ONBOARDING_CODE:
        raise HTTPException(status_code=403, detail="入职链接口令无效")

    payload = data.model_dump(exclude_none=True)
    if "id_card" in payload:
        payload["id_card"] = _normalize_id_card_value(payload.get("id_card"))
        _validate_and_normalize_id_card(payload.get("id_card"))
    extra_fields = payload.pop("extra_fields", {}) or {}
    source_record = {**payload, **extra_fields}
    cleaned, extra = normalize_record(source_record)

    required_fields = {
        "name": "姓名",
        "mobile": "手机号",
        "id_card": "身份证号",
        "subject": "任教学科",
        "education": "学历",
        "graduate_school": "毕业院校",
        "major": "专业",
        "political_status": "政治面貌",
        "address": "家庭住址",
        "ethnicity": "民族",
        "native_place": "籍贯",
        "email": "电子邮件",
    }
    missing = []
    for key, label in required_fields.items():
        val = cleaned.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            val = extra.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(label)
    if missing:
        raise HTTPException(status_code=400, detail=f"以下字段为必填：{'、'.join(missing)}")

    conn = get_connection()
    try:
        existing, _ = find_existing_teacher_with_reason(conn, cleaned)
        teacher_id: int
        if existing:
            merge_teacher(conn, existing, cleaned, extra, merge_policy="fill_missing")
            teacher_id = int(existing["id"])
        else:
            teacher_id = int(insert_teacher(conn, cleaned, extra))

        username, password = _create_or_reset_teacher_account(conn, teacher_id)
        conn.commit()
        return {
            "teacher_id": teacher_id,
            "username": username,
            "password": password,
            "message": "提交成功，账号已创建（或重置）"
        }
    finally:
        conn.close()


@router.put("/{teacher_id}")
async def update_teacher(teacher_id: int, data: TeacherUpdate, user: dict = Depends(get_current_user)):
    """更新教师信息"""
    if user.get("role") == "teacher" and user.get("teacher_id") != teacher_id:
        raise HTTPException(status_code=403, detail="无权限")
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="浏览账号不允许修改")

    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="教师不存在")

        raw_update = data.model_dump(exclude_none=True, exclude={"extra_fields"})
        if "id_card" in raw_update:
            raw_update["id_card"] = _normalize_id_card_value(raw_update.get("id_card"))
            _validate_and_normalize_id_card(raw_update.get("id_card"))
        update_data = {k: v for k, v in raw_update.items() if k in BUILTIN_FIELDS}
        merged_extra_fields = dict(data.extra_fields or {})
        for k, v in raw_update.items():
            if k not in BUILTIN_FIELDS and v is not None:
                merged_extra_fields[k] = str(v)
        payload = {"update_data": update_data, "extra_fields": merged_extra_fields}

        if user.get("role") == "teacher":
            request_id = _create_change_request(conn, teacher_id, user["id"], "update_teacher", payload)
            conn.commit()
            return {"pending": True, "request_id": request_id, "message": "已提交管理员审核"}

        row = _apply_teacher_update(conn, teacher_id, payload)
        conn.commit()
        return row_to_teacher_response(dict(row), conn)
    finally:
        conn.close()


@router.delete("/{teacher_id}")
async def delete_teacher(teacher_id: int, user: dict = Depends(get_current_user)):
    """删除教师"""
    require_admin(user)
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
async def add_tag(teacher_id: int, tag: str = Query(..., description="标签名称"), user: dict = Depends(get_current_user)):
    """添加标签"""
    if user.get("role") == "teacher" and user.get("teacher_id") != teacher_id:
        raise HTTPException(status_code=403, detail="无权限")
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="浏览账号不允许修改")
    conn = get_connection()
    try:
        existed = conn.execute("SELECT id FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
        if not existed:
            raise HTTPException(status_code=404, detail="教师不存在")

        if user.get("role") == "teacher":
            request_id = _create_change_request(conn, teacher_id, user["id"], "add_tag", {"tag": tag})
            conn.commit()
            return {"pending": True, "request_id": request_id, "message": "已提交管理员审核"}

        tags = _apply_tag_change(conn, teacher_id, tag, "add")
        conn.commit()
        return {"tags": tags}
    finally:
        conn.close()


@router.delete("/{teacher_id}/tags")
async def remove_tag(teacher_id: int, tag: str = Query(..., description="标签名称"), user: dict = Depends(get_current_user)):
    """删除标签"""
    if user.get("role") == "teacher" and user.get("teacher_id") != teacher_id:
        raise HTTPException(status_code=403, detail="无权限")
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="浏览账号不允许修改")
    conn = get_connection()
    try:
        existed = conn.execute("SELECT id FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
        if not existed:
            raise HTTPException(status_code=404, detail="教师不存在")

        if user.get("role") == "teacher":
            request_id = _create_change_request(conn, teacher_id, user["id"], "remove_tag", {"tag": tag})
            conn.commit()
            return {"pending": True, "request_id": request_id, "message": "已提交管理员审核"}

        tags = _apply_tag_change(conn, teacher_id, tag, "remove")
        conn.commit()
        return {"tags": tags}
    finally:
        conn.close()


@router.get("/{teacher_id}/logs", response_model=list[ChangeLogResponse])
async def get_teacher_logs(teacher_id: int, user: dict = Depends(get_current_user)):
    """获取教师修改记录"""
    if user.get("role") == "teacher" and user.get("teacher_id") != teacher_id:
        raise HTTPException(status_code=403, detail="无权限")
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
async def batch_update(teacher_ids: list[int], field: str, value: str, user: dict = Depends(get_current_user)):
    """批量修改教师字段"""
    require_admin(user)
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


@router.post("/{teacher_id}/avatar")
async def upload_teacher_avatar(
    teacher_id: int,
    file: UploadFile = File(...),
    cover_color: str = Form(""),
    user: dict = Depends(get_current_user)
):
    """上传教师头像并可同步设置封面主题色"""
    if user.get("role") == "teacher" and user.get("teacher_id") != teacher_id:
        raise HTTPException(status_code=403, detail="无权限")
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="浏览账号不允许修改")

    ext = _safe_ext(file.filename or "")
    if not ext:
        raise HTTPException(status_code=400, detail="仅支持 png/jpg/jpeg/webp 图片")

    os.makedirs(AVATAR_DIR, exist_ok=True)
    token = secrets.token_hex(8)
    rel_path = f"avatars/t{teacher_id}_{token}{ext}"
    abs_path = os.path.join(UPLOAD_DIR, rel_path)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="头像文件为空")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="头像文件不能超过 5MB")

    with open(abs_path, "wb") as f:
        f.write(content)

    avatar_url = f"/uploads/{rel_path}"
    color = _normalize_cover_color(cover_color)

    conn = get_connection()
    try:
        existed = conn.execute("SELECT id FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
        if not existed:
            raise HTTPException(status_code=404, detail="教师不存在")

        if user.get("role") == "teacher":
            request_id = _create_change_request(
                conn,
                teacher_id,
                user["id"],
                "update_avatar",
                {"avatar_url": avatar_url, "cover_color": color}
            )
            conn.commit()
            return {"pending": True, "request_id": request_id, "message": "已提交管理员审核"}

        _apply_avatar_update(conn, teacher_id, avatar_url, color)
        conn.commit()
        return {"avatar_url": avatar_url, "cover_color": color}
    finally:
        conn.close()


@router.post("/{teacher_id}/profile-theme")
async def update_teacher_profile_theme(
    teacher_id: int,
    cover_color: str = Form(...),
    user: dict = Depends(get_current_user)
):
    """更新教师详情封面主题色"""
    if user.get("role") == "teacher" and user.get("teacher_id") != teacher_id:
        raise HTTPException(status_code=403, detail="无权限")
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="浏览账号不允许修改")

    color = _normalize_cover_color(cover_color)
    if not color:
        raise HTTPException(status_code=400, detail="主题色格式不正确，应为 #RRGGBB")

    conn = get_connection()
    try:
        existed = conn.execute("SELECT id FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
        if not existed:
            raise HTTPException(status_code=404, detail="教师不存在")
        if user.get("role") == "teacher":
            request_id = _create_change_request(
                conn, teacher_id, user["id"], "update_theme", {"cover_color": color}
            )
            conn.commit()
            return {"pending": True, "request_id": request_id, "message": "已提交管理员审核"}

        _apply_profile_theme(conn, teacher_id, color)
        conn.commit()
    finally:
        conn.close()

    return {"cover_color": color}


@router.get("/audit/change-requests")
async def list_change_requests(
    status: str = Query("pending", description="pending/approved/rejected/all"),
    teacher_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user)
):
    require_admin(user)
    conn = get_connection()
    try:
        conditions = []
        params: list[Any] = []
        if status != "all":
            conditions.append("r.status = ?")
            params.append(status)
        if teacher_id is not None:
            conditions.append("r.teacher_id = ?")
            params.append(teacher_id)
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        rows = conn.execute(
            "SELECT r.*, u.username AS requester_username, t.name AS teacher_name "
            "FROM teacher_change_requests r "
            "LEFT JOIN users u ON u.id = r.requester_user_id "
            "LEFT JOIN teachers t ON t.id = r.teacher_id "
            f"WHERE {where_clause} "
            "ORDER BY r.created_at DESC LIMIT ?",
            params + [limit]
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/audit/change-requests/{request_id}/approve")
async def approve_change_request(request_id: int, user: dict = Depends(get_current_user)):
    require_admin(user)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM teacher_change_requests WHERE id = ?",
            (request_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="审核请求不存在")
        request_row = dict(row)
        if request_row["status"] != "pending":
            raise HTTPException(status_code=400, detail="该请求已处理")

        _apply_change_request(conn, request_row)
        conn.execute(
            "UPDATE teacher_change_requests SET status = 'approved', reviewer_user_id = ?, reviewed_at = ? WHERE id = ?",
            (user["id"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), request_id)
        )
        conn.commit()
        return {"message": "已通过并生效"}
    finally:
        conn.close()


@router.post("/audit/change-requests/{request_id}/reject")
async def reject_change_request(
    request_id: int,
    note: str = Form(""),
    user: dict = Depends(get_current_user)
):
    require_admin(user)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT status FROM teacher_change_requests WHERE id = ?",
            (request_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="审核请求不存在")
        if row["status"] != "pending":
            raise HTTPException(status_code=400, detail="该请求已处理")

        conn.execute(
            "UPDATE teacher_change_requests SET status = 'rejected', reviewer_user_id = ?, review_note = ?, reviewed_at = ? WHERE id = ?",
            (user["id"], (note or "").strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), request_id)
        )
        conn.commit()
        return {"message": "已驳回"}
    finally:
        conn.close()

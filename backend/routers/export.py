"""
数据导出路由
"""
import os
import json
from datetime import datetime
from fastapi import APIRouter, Query, Depends
from fastapi.responses import FileResponse
from typing import Optional
from backend.database import get_connection
from backend.config import EXPORT_DIR
from backend.services.auth_utils import get_current_user, require_roles

router = APIRouter(prefix="/api/export", tags=["数据导出"])


@router.get("/excel")
async def export_excel(
    keyword: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    birth_date: Optional[str] = Query(None),
    political_status: Optional[str] = Query(None),
    education: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
    original_unit: Optional[str] = Query(None),
    public_service_time: Optional[str] = Query(None),
    car_plate: Optional[str] = Query(None),
    graduate_school: Optional[str] = Query(None),
    ethnicity: Optional[str] = Query(None),
    address: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    hire_date: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """将筛选结果导出为 Excel"""
    import pandas as pd
    require_roles(user, {"admin", "viewer"})

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
        if subject:
            conditions.append("subject LIKE ?")
            params.append(f"%{subject}%")
        if hire_date:
            conditions.append("hire_date LIKE ?")
            params.append(f"%{hire_date}%")
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
        if original_unit:
            add_extra_like(extra_field_aliases["original_unit"], original_unit)
        if public_service_time:
            add_extra_like(extra_field_aliases["public_service_time"], public_service_time)
        if car_plate:
            add_extra_like(extra_field_aliases["car_plate"], car_plate, "%车牌%")

        where = " AND ".join(conditions) if conditions else "1=1"

        rows = conn.execute(
            f"SELECT * FROM teachers WHERE {where} ORDER BY id", params
        ).fetchall()

        # 转换为 DataFrame
        data = []
        for row in rows:
            r = dict(row)
            # 获取扩展字段
            extras = conn.execute(
                "SELECT field_name, field_value FROM teacher_extra_fields WHERE teacher_id = ?",
                (r["id"],)
            ).fetchall()
            for extra in extras:
                r[extra["field_name"]] = extra["field_value"]

            # 处理标签
            try:
                r["tags"] = ", ".join(json.loads(r.get("tags") or "[]"))
            except (json.JSONDecodeError, TypeError):
                r["tags"] = ""

            # 删除不需要导出的字段
            r.pop("id", None)
            r.pop("created_at", None)
            r.pop("updated_at", None)

            data.append(r)

        df = pd.DataFrame(data)

        # 列名映射为中文
        column_map = {
            "name": "姓名", "gender": "性别", "id_card": "身份证号",
            "phone": "联系电话", "mobile": "手机", "short_phone": "小号",
            "birth_date": "出生日期", "age": "年龄",
            "graduate_school": "毕业院校", "education": "学历",
            "political_status": "政治面貌", "ethnicity": "民族",
            "native_place": "籍贯", "address": "地址",
            "email": "邮箱", "title": "职称", "position": "职务",
            "subject": "任教学科", "hire_date": "入职日期",
            "employee_id": "工号", "tags": "标签"
        }
        df.rename(columns=column_map, inplace=True)

        # 保存文件
        os.makedirs(EXPORT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"教师数据_{timestamp}.xlsx"
        filepath = os.path.join(EXPORT_DIR, filename)
        df.to_excel(filepath, index=False, engine="openpyxl")

        return FileResponse(
            filepath,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    finally:
        conn.close()

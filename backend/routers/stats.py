"""
统计分析路由
"""
from fastapi import APIRouter, Depends
from backend.database import get_connection
from backend.models import StatsResponse
from backend.services.id_card_utils import extract_birth_date, calculate_age, validate_id_card
from backend.services.auth_utils import get_current_user, require_roles

router = APIRouter(prefix="/api/stats", tags=["统计分析"])


@router.get("/", response_model=StatsResponse)
async def get_stats(user=Depends(get_current_user)):
    """获取教师统计数据"""
    require_roles(user, {"admin", "viewer"})
    conn = get_connection()
    try:
        # 总人数
        total = conn.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]

        # 性别统计
        gender_rows = conn.execute(
            "SELECT COALESCE(gender, '未知') as g, COUNT(*) as c FROM teachers GROUP BY gender"
        ).fetchall()
        gender_stats = {row["g"]: row["c"] for row in gender_rows}

        # 年龄分布
        def normalize_birth_date(raw: str | None) -> str | None:
            if not raw:
                return None
            val = str(raw).strip()
            if not val:
                return None
            if val.isdigit() and len(val) == 8:
                return f"{val[0:4]}-{val[4:6]}-{val[6:8]}"
            val = val.replace("/", "-").replace(".", "-")
            if len(val) >= 10:
                return val[:10]
            return val

        def compute_age_from_row(row) -> int | None:
            id_card = row["id_card"]
            birth_date = row["birth_date"]
            age_val = row["age"]

            if id_card and validate_id_card(id_card):
                derived = extract_birth_date(id_card)
                if derived:
                    return calculate_age(derived)

            normalized = normalize_birth_date(birth_date)
            if normalized:
                age = calculate_age(normalized)
                if age is not None:
                    return age

            try:
                return int(age_val) if age_val is not None else None
            except (TypeError, ValueError):
                return None

        age_stats = {}
        age_ranges = [
            ("25岁以下", lambda a: a < 25),
            ("25-30岁", lambda a: a >= 25 and a < 30),
            ("30-35岁", lambda a: a >= 30 and a < 35),
            ("35-40岁", lambda a: a >= 35 and a < 40),
            ("40-45岁", lambda a: a >= 40 and a < 45),
            ("45-50岁", lambda a: a >= 45 and a < 50),
            ("50-55岁", lambda a: a >= 50 and a < 55),
            ("55岁以上", lambda a: a >= 55),
        ]

        counts = {label: 0 for label, _ in age_ranges}
        unknown = 0
        rows = conn.execute("SELECT id_card, birth_date, age FROM teachers").fetchall()
        for row in rows:
            age = compute_age_from_row(row)
            if age is None:
                unknown += 1
                continue
            placed = False
            for label, fn in age_ranges:
                if fn(age):
                    counts[label] += 1
                    placed = True
                    break
            if not placed:
                unknown += 1

        for label, cnt in counts.items():
            if cnt > 0:
                age_stats[label] = cnt
        if unknown > 0:
            age_stats["未知"] = unknown

        # 学历统计
        edu_rows = conn.execute(
            "SELECT COALESCE(education, '未知') as e, COUNT(*) as c FROM teachers GROUP BY education"
        ).fetchall()
        education_stats = {row["e"]: row["c"] for row in edu_rows}

        # 政治面貌统计
        pol_rows = conn.execute(
            "SELECT COALESCE(political_status, '未知') as p, COUNT(*) as c FROM teachers GROUP BY political_status"
        ).fetchall()
        political_stats = {row["p"]: row["c"] for row in pol_rows}

        return StatsResponse(
            total_teachers=total,
            gender_stats=gender_stats,
            age_stats=age_stats,
            education_stats=education_stats,
            political_stats=political_stats
        )
    finally:
        conn.close()


@router.get("/tags")
async def get_tag_stats(user=Depends(get_current_user)):
    """获取标签统计"""
    require_roles(user, {"admin", "viewer"})
    conn = get_connection()
    try:
        import json
        rows = conn.execute("SELECT tags FROM teachers WHERE tags IS NOT NULL AND tags != '[]'").fetchall()
        tag_counts = {}
        for row in rows:
            try:
                tags = json.loads(row["tags"])
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass
        return tag_counts
    finally:
        conn.close()


@router.get("/fields")
async def get_field_stats(user=Depends(get_current_user)):
    """获取所有已注册字段"""
    require_roles(user, {"admin", "viewer"})
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT field_name, display_name, field_type, is_builtin FROM field_registry ORDER BY is_builtin DESC, id ASC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/titles")
async def get_title_options(user=Depends(get_current_user)):
    """获取职称下拉选项"""
    require_roles(user, {"admin", "viewer"})
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT title FROM teachers WHERE title IS NOT NULL AND TRIM(title) != '' ORDER BY title"
        ).fetchall()
        return [row["title"] for row in rows if row["title"]]
    finally:
        conn.close()


@router.get("/logs")
async def get_recent_logs(limit: int = 50, user=Depends(get_current_user)):
    """获取最近操作日志"""
    require_roles(user, {"admin", "viewer"})
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM change_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

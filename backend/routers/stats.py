"""
统计分析路由
"""
import re
from datetime import date
from fastapi import APIRouter, Depends
from backend.database import get_connection
from backend.models import StatsResponse
from backend.services.id_card_utils import extract_birth_date, calculate_age, validate_id_card
from backend.services.auth_utils import get_current_user, require_roles

router = APIRouter(prefix="/api/stats", tags=["统计分析"])


def _normalize_birth_date(raw: str | None) -> str | None:
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


def _compute_age_from_row(row) -> int | None:
    id_card = row["id_card"]
    birth_date = row["birth_date"]
    age_val = row["age"]

    if id_card and validate_id_card(id_card):
        derived = extract_birth_date(id_card)
        if derived:
            return calculate_age(derived)

    normalized = _normalize_birth_date(birth_date)
    if normalized:
        age = calculate_age(normalized)
        if age is not None:
            return age

    try:
        return int(age_val) if age_val is not None else None
    except (TypeError, ValueError):
        return None


def _parse_year(value: str | None) -> int | None:
    if not value:
        return None
    m = re.search(r"(19|20)\d{2}", str(value))
    if not m:
        return None
    y = int(m.group(0))
    if y < 1950 or y > date.today().year:
        return None
    return y


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
            age = _compute_age_from_row(row)
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


@router.get("/advanced")
async def get_advanced_stats(user=Depends(get_current_user)):
    """获取增强统计数据"""
    require_roles(user, {"admin", "viewer"})
    conn = get_connection()
    try:
        teacher_rows = conn.execute(
            "SELECT id, gender, id_card, birth_date, age, title, subject, graduate_school, education, political_status, hire_date, mobile, phone, email "
            "FROM teachers"
        ).fetchall()
        total = len(teacher_rows)

        # 扩展字段缓存：teacher_id -> {field: value}
        extra_rows = conn.execute(
            "SELECT teacher_id, field_name, field_value FROM teacher_extra_fields"
        ).fetchall()
        extra_map: dict[int, dict[str, str]] = {}
        for row in extra_rows:
            tid = int(row["teacher_id"])
            extra_map.setdefault(tid, {})[row["field_name"]] = row["field_value"]

        title_stats: dict[str, int] = {}
        subject_stats: dict[str, int] = {}
        school_stats: dict[str, int] = {}
        hire_year_stats: dict[str, int] = {}
        work_years_stats = {
            "0-5年": 0,
            "6-10年": 0,
            "11-20年": 0,
            "21年以上": 0,
            "未知": 0,
        }

        party_member_count = 0
        under_35_count = 0
        senior_title_count = 0
        filled_mobile = 0
        filled_phone = 0
        filled_email = 0
        filled_subject = 0
        filled_title = 0
        filled_education = 0

        current_year = date.today().year
        for row in teacher_rows:
            d = dict(row)
            tid = int(d["id"])
            extra = extra_map.get(tid, {})

            title = (d.get("title") or "").strip() or "未知"
            subject = (d.get("subject") or "").strip() or "未知"
            school = (d.get("graduate_school") or "").strip() or "未知"
            political = (d.get("political_status") or "").strip()
            education = (d.get("education") or "").strip()

            title_stats[title] = title_stats.get(title, 0) + 1
            subject_stats[subject] = subject_stats.get(subject, 0) + 1
            school_stats[school] = school_stats.get(school, 0) + 1

            if political in {"中共党员", "中共预备党员"}:
                party_member_count += 1
            if title not in {"未知", ""} and ("高级" in title or "正高" in title or "副高" in title):
                senior_title_count += 1

            if (d.get("mobile") or "").strip():
                filled_mobile += 1
            if (d.get("phone") or "").strip():
                filled_phone += 1
            if (d.get("email") or "").strip():
                filled_email += 1
            if subject and subject != "未知":
                filled_subject += 1
            if title and title != "未知":
                filled_title += 1
            if education:
                filled_education += 1

            age = _compute_age_from_row(row)
            if age is not None and age < 35:
                under_35_count += 1

            hire_year = _parse_year(d.get("hire_date")) or _parse_year(extra.get("参加工作时间")) or _parse_year(extra.get("参公时间"))
            if hire_year:
                k = str(hire_year)
                hire_year_stats[k] = hire_year_stats.get(k, 0) + 1
                years = current_year - hire_year
                if years <= 5:
                    work_years_stats["0-5年"] += 1
                elif years <= 10:
                    work_years_stats["6-10年"] += 1
                elif years <= 20:
                    work_years_stats["11-20年"] += 1
                else:
                    work_years_stats["21年以上"] += 1
            else:
                work_years_stats["未知"] += 1

        school_top = sorted(
            [{"name": k, "count": v} for k, v in school_stats.items() if k != "未知"],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        title_top = sorted(
            [{"name": k, "count": v} for k, v in title_stats.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        subject_top = sorted(
            [{"name": k, "count": v} for k, v in subject_stats.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:12]

        sorted_hire_year_stats = dict(sorted(hire_year_stats.items(), key=lambda kv: kv[0]))
        subject_count = len([k for k in subject_stats.keys() if k and k != "未知"])

        def _ratio(v: int) -> float:
            return round((v / total), 4) if total > 0 else 0.0

        completeness = [
            {"field": "手机", "filled": filled_mobile, "total": total, "ratio": _ratio(filled_mobile)},
            {"field": "联系电话", "filled": filled_phone, "total": total, "ratio": _ratio(filled_phone)},
            {"field": "邮箱", "filled": filled_email, "total": total, "ratio": _ratio(filled_email)},
            {"field": "学科", "filled": filled_subject, "total": total, "ratio": _ratio(filled_subject)},
            {"field": "职称", "filled": filled_title, "total": total, "ratio": _ratio(filled_title)},
            {"field": "学历", "filled": filled_education, "total": total, "ratio": _ratio(filled_education)},
        ]

        return {
            "party_member_count": party_member_count,
            "under_35_count": under_35_count,
            "senior_title_count": senior_title_count,
            "subject_count": subject_count,
            "title_stats": title_stats,
            "subject_stats": subject_stats,
            "work_years_stats": work_years_stats,
            "hire_year_stats": sorted_hire_year_stats,
            "graduate_school_top": school_top,
            "title_top": title_top,
            "subject_top": subject_top,
            "completeness": completeness,
        }
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

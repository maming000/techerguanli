"""
人格测评（大五）模块
"""
import json
import os
import random
from datetime import datetime
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.config import FRONTEND_DIR
from backend.database import get_connection
from backend.services.auth_utils import get_current_user, require_roles

router = APIRouter(prefix="/api/assessment", tags=["人格测评"])

TRAIT_KEYS = {
    "O": "openness",
    "C": "conscientiousness",
    "E": "extraversion",
    "A": "agreeableness",
    "N": "neuroticism",
}


class SubmitAssessmentRequest(BaseModel):
    question_ids: list[int]
    answers: list[int]


def _score_item(answer: int, reverse: bool) -> int:
    return (6 - answer) if reverse else answer


def _normalize_avg(avg_1_to_5: float) -> float:
    return round((avg_1_to_5 - 1.0) / 4.0 * 100.0, 2)


@lru_cache(maxsize=1)
def load_questions_meta():
    path = os.path.join(FRONTEND_DIR, "js", "assessment", "ipip50_questions.json")
    if not os.path.exists(path):
        raise RuntimeError("测评题库文件不存在")
    with open(path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    if not isinstance(rows, list) or len(rows) != 50:
        raise RuntimeError("测评题库格式错误，必须为50题")

    trait_counts = {k: 0 for k in TRAIT_KEYS.keys()}
    parsed = []
    for row in rows:
        trait = str(row.get("trait", "")).strip().upper()
        if trait not in TRAIT_KEYS:
            raise RuntimeError(f"测评题库trait错误: {trait}")
        reverse = bool(row.get("reverse", False))
        qid = int(row.get("id", 0))
        text = str(row.get("text", "")).strip()
        text_zh = str(row.get("text_zh", "")).strip()
        if qid <= 0 or not text:
            raise RuntimeError("测评题库题目格式错误")
        parsed.append({
            "id": qid,
            "text": text,
            "text_zh": text_zh,
            "trait": trait,
            "reverse": reverse
        })
        trait_counts[trait] += 1

    for trait, count in trait_counts.items():
        if count != 10:
            raise RuntimeError(f"测评题库分布错误: {trait} 应为10题，实际{count}题")

    return parsed


def _get_client_ip(request: Request) -> str:
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        return xff.split(",")[0].strip()
    xri = (request.headers.get("x-real-ip") or "").strip()
    if xri:
        return xri
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@router.get("/questions")
async def get_assessment_questions(user=Depends(get_current_user)):
    if user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="仅教师账号可参与测评")

    rows = load_questions_meta()
    by_trait = {k: [] for k in TRAIT_KEYS.keys()}
    for q in rows:
        by_trait[q["trait"]].append(q)

    # 每次测评 30 题：五维各抽 6 题，保持维度平衡
    picked = []
    for trait in ["O", "C", "E", "A", "N"]:
        pool = by_trait.get(trait, [])
        if len(pool) < 6:
            raise HTTPException(status_code=500, detail=f"{trait} 维度题量不足")
        picked.extend(random.sample(pool, 6))
    random.shuffle(picked)

    return [
        {
            "id": int(q["id"]),
            "text": q["text"],
            "text_zh": q["text_zh"] or q["text"],
        }
        for q in picked
    ]


@router.post("/submit")
async def submit_assessment(data: SubmitAssessmentRequest, request: Request, user=Depends(get_current_user)):
    # 教师可提交，管理员/浏览账号不可提交个人测评
    if user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="仅教师账号可提交测评")

    question_ids = data.question_ids or []
    answers = data.answers or []
    if len(question_ids) != 30 or len(answers) != 30:
        raise HTTPException(status_code=400, detail="本次测评需提交30题及对应答案")
    if len(set(question_ids)) != 30:
        raise HTTPException(status_code=400, detail="题目列表存在重复")

    for idx, a in enumerate(answers, start=1):
        if not isinstance(a, int) or a < 1 or a > 5:
            raise HTTPException(status_code=400, detail=f"第{idx}题答案无效，必须为1-5")

    question_meta = load_questions_meta()
    question_map = {int(q["id"]): q for q in question_meta}
    chosen = []
    trait_counter = {k: 0 for k in TRAIT_KEYS.keys()}
    for qid in question_ids:
        q = question_map.get(int(qid))
        if not q:
            raise HTTPException(status_code=400, detail=f"题目ID无效: {qid}")
        chosen.append(q)
        trait_counter[q["trait"]] += 1
    # 严格校验每个维度 6 题
    for trait in ["O", "C", "E", "A", "N"]:
        if trait_counter[trait] != 6:
            raise HTTPException(status_code=400, detail="题目分布无效，请重新开始测评")

    sums = {k: 0.0 for k in TRAIT_KEYS.values()}
    counts = {k: 0 for k in TRAIT_KEYS.values()}
    answer_items = []
    for i, meta in enumerate(chosen):
        trait_key = TRAIT_KEYS[meta["trait"]]
        score = _score_item(answers[i], meta["reverse"])
        sums[trait_key] += score
        counts[trait_key] += 1
        answer_items.append({
            "id": int(meta["id"]),
            "text_zh": meta["text_zh"] or meta["text"],
            "answer": int(answers[i])
        })

    avgs = {k: (sums[k] / counts[k] if counts[k] else 0.0) for k in sums.keys()}
    normalized = {k: _normalize_avg(avgs[k]) for k in avgs.keys()}

    user_id = str(user["id"])
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO personality_tests "
            "(user_id, question_ids, answers, answer_items, client_ip, openness, conscientiousness, extraversion, agreeableness, neuroticism, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                json.dumps(question_ids, ensure_ascii=False),
                json.dumps(answers, ensure_ascii=False),
                json.dumps(answer_items, ensure_ascii=False),
                _get_client_ip(request),
                normalized["openness"],
                normalized["conscientiousness"],
                normalized["extraversion"],
                normalized["agreeableness"],
                normalized["neuroticism"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        test_id = int(cur.lastrowid)
        return {
            "id": test_id,
            "scores": normalized,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "disclaimer": "This assessment is for reference only and not a clinical diagnosis.",
        }
    finally:
        conn.close()


@router.get("/history")
async def get_assessment_history(user=Depends(get_current_user)):
    # 教师只能看自己的历史；管理员不看个体结果
    if user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="仅教师账号可查看个人测评历史")

    user_id = str(user["id"])
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, openness, conscientiousness, extraversion, agreeableness, neuroticism, created_at "
            "FROM personality_tests WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": int(r["id"]),
                "scores": {
                    "openness": float(r["openness"] or 0),
                    "conscientiousness": float(r["conscientiousness"] or 0),
                    "extraversion": float(r["extraversion"] or 0),
                    "agreeableness": float(r["agreeableness"] or 0),
                    "neuroticism": float(r["neuroticism"] or 0),
                },
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        conn.close()


@router.get("/admin-records")
async def get_admin_records(limit: int = 100, user=Depends(get_current_user)):
    require_roles(user, {"admin"})
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT p.id, p.user_id, p.client_ip, p.created_at, p.answer_items, "
            "p.openness, p.conscientiousness, p.extraversion, p.agreeableness, p.neuroticism, "
            "u.username "
            "FROM personality_tests p "
            "LEFT JOIN users u ON CAST(u.id AS TEXT) = p.user_id "
            "ORDER BY p.created_at DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        ).fetchall()

        result = []
        for r in rows:
            try:
                items = json.loads(r["answer_items"] or "[]")
            except Exception:
                items = []
            result.append({
                "id": int(r["id"]),
                "user_id": r["user_id"],
                "username": r["username"] or f"user_{r['user_id']}",
                "client_ip": r["client_ip"] or "-",
                "created_at": r["created_at"],
                "scores": {
                    "openness": float(r["openness"] or 0),
                    "conscientiousness": float(r["conscientiousness"] or 0),
                    "extraversion": float(r["extraversion"] or 0),
                    "agreeableness": float(r["agreeableness"] or 0),
                    "neuroticism": float(r["neuroticism"] or 0),
                },
                "answer_items": items
            })
        return result
    finally:
        conn.close()


@router.get("/stats")
async def get_assessment_stats(user=Depends(get_current_user)):
    # 管理员仅可看汇总统计，不返回任何个人明细
    require_roles(user, {"admin"})
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT openness, conscientiousness, extraversion, agreeableness, neuroticism, created_at FROM personality_tests"
        ).fetchall()
        total = len(rows)

        traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
        averages = {k: 0.0 for k in traits}
        distributions = {
            k: {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
            for k in traits
        }
        trend = {}

        if total > 0:
            for r in rows:
                for k in traits:
                    val = float(r[k] or 0)
                    averages[k] += val
                    if val <= 20:
                        distributions[k]["0-20"] += 1
                    elif val <= 40:
                        distributions[k]["21-40"] += 1
                    elif val <= 60:
                        distributions[k]["41-60"] += 1
                    elif val <= 80:
                        distributions[k]["61-80"] += 1
                    else:
                        distributions[k]["81-100"] += 1
                day = str(r["created_at"] or "")[:10]
                if day:
                    trend[day] = trend.get(day, 0) + 1
            for k in traits:
                averages[k] = round(averages[k] / total, 2)

        trend_rows = [{"date": k, "count": trend[k]} for k in sorted(trend.keys())]
        return {
            "total_tests": total,
            "averages": averages,
            "distributions": distributions,
            "trend": trend_rows,
            "disclaimer": "This assessment is for reference only and not a clinical diagnosis.",
        }
    finally:
        conn.close()

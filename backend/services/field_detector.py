"""
字段自动识别服务
识别上传文件中的字段，自动映射到系统字段或注册新字段
"""
import re
from backend.config import FIELD_MAPPING, BUILTIN_FIELDS
from backend.database import get_connection


def normalize_field_name(raw_name: str) -> str:
    """
    清理字段名称：去除空格、换行、特殊字符
    """
    if not raw_name:
        return ""
    # 去除空白字符
    name = re.sub(r'\s+', '', str(raw_name).strip())
    # 去除常见括号备注
    name = re.sub(r'[（(].*?[）)]', '', name)
    return name


def detect_field(raw_name: str) -> tuple[str, bool]:
    """
    检测字段名并返回映射后的英文字段名
    返回: (field_name, is_builtin)
    """
    clean_name = normalize_field_name(raw_name)
    if not clean_name:
        return ("", False)

    # 先尝试精确匹配
    if clean_name in FIELD_MAPPING:
        return (FIELD_MAPPING[clean_name], True)

    # 模糊匹配：包含关键词
    for cn_name, en_name in FIELD_MAPPING.items():
        if cn_name in clean_name or clean_name in cn_name:
            return (en_name, True)

    # 未识别字段，返回清理后的中文名作为扩展字段
    return (clean_name, False)


def register_new_field(field_name: str, display_name: str = None):
    """
    注册新发现的字段到字段注册表
    """
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO field_registry (field_name, display_name, field_type, is_builtin) VALUES (?, ?, 'TEXT', 0)",
            (field_name, display_name or field_name)
        )
        conn.commit()
    finally:
        conn.close()


def get_all_fields() -> list[dict]:
    """
    获取所有已注册字段
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT field_name, display_name, field_type, is_builtin FROM field_registry ORDER BY is_builtin DESC, id ASC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def map_headers(headers: list[str]) -> dict:
    """
    将表头列表映射为 {列索引: (字段名, 是否内置)} 的字典
    同时注册新发现的字段
    """
    mapping = {}
    new_fields = []

    for idx, header in enumerate(headers):
        field_name, is_builtin = detect_field(header)
        if not field_name:
            continue

        mapping[idx] = (field_name, is_builtin)

        if not is_builtin:
            register_new_field(field_name, normalize_field_name(header))
            new_fields.append(field_name)

    return mapping, new_fields

"""
身份证工具 - 从身份证号提取出生日期和计算年龄
"""
from datetime import datetime, date
import re


def extract_birth_date(id_card: str) -> str | None:
    """
    从18位身份证号中提取出生日期
    返回格式：YYYY-MM-DD
    """
    if not id_card or not isinstance(id_card, str):
        return None

    # 清理空格
    id_card = id_card.strip()

    # 18位身份证号
    if len(id_card) == 18:
        year = id_card[6:10]
        month = id_card[10:12]
        day = id_card[12:14]
        try:
            birth = datetime(int(year), int(month), int(day))
            return birth.strftime("%Y-%m-%d")
        except ValueError:
            return None

    # 15位旧版身份证号
    if len(id_card) == 15:
        year = "19" + id_card[6:8]
        month = id_card[8:10]
        day = id_card[10:12]
        try:
            birth = datetime(int(year), int(month), int(day))
            return birth.strftime("%Y-%m-%d")
        except ValueError:
            return None

    return None


def calculate_age(birth_date_str: str) -> int | None:
    """
    根据出生日期计算年龄
    """
    if not birth_date_str:
        return None

    try:
        birth = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        today = date.today()
        age = today.year - birth.year
        if (today.month, today.day) < (birth.month, birth.day):
            age -= 1
        return age
    except (ValueError, TypeError):
        return None


def extract_gender_from_id(id_card: str) -> str | None:
    """
    从身份证号提取性别
    18位身份证第17位：奇数为男，偶数为女
    """
    if not id_card or not isinstance(id_card, str):
        return None

    id_card = id_card.strip()
    if len(id_card) == 18:
        try:
            return "男" if int(id_card[16]) % 2 == 1 else "女"
        except (ValueError, IndexError):
            return None
    elif len(id_card) == 15:
        try:
            return "男" if int(id_card[14]) % 2 == 1 else "女"
        except (ValueError, IndexError):
            return None
    return None


def validate_id_card(id_card: str) -> bool:
    """
    验证身份证号是否合法（基本格式校验）
    """
    if not id_card or not isinstance(id_card, str):
        return False

    id_card = id_card.strip()

    # 18位身份证
    if len(id_card) == 18:
        if not re.match(r'^\d{17}[\dXx]$', id_card):
            return False
        # 校验码验证
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = '10X98765432'
        try:
            total = sum(int(id_card[i]) * weights[i] for i in range(17))
            expected = check_codes[total % 11]
            return id_card[17].upper() == expected
        except (ValueError, IndexError):
            return False

    # 15位身份证
    if len(id_card) == 15:
        return bool(re.match(r'^\d{15}$', id_card))

    return False

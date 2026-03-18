"""
配置文件 - 教师信息管理系统
"""
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据库配置
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "teachers.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# 上传文件目录
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# 导出文件目录
EXPORT_DIR = os.path.join(BASE_DIR, "exports")

# 前端静态文件目录
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# 允许上传的文件类型
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".docx", ".doc"}

# 分页默认设置
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# 确保必要目录存在
for d in [DATABASE_DIR, UPLOAD_DIR, EXPORT_DIR]:
    os.makedirs(d, exist_ok=True)

# 内置字段映射：中文名 -> 英文字段名
FIELD_MAPPING = {
    "姓名": "name",
    "名字": "name",
    "教师姓名": "name",
    "性别": "gender",
    "身份证号": "id_card",
    "身份证": "id_card",
    "身份证号码": "id_card",
    "联系电话": "phone",
    "电话": "phone",
    "座机": "phone",
    "手机": "mobile",
    "手机号": "mobile",
    "手机号码": "mobile",
    "移动电话": "mobile",
    "小号": "short_phone",
    "短号": "short_phone",
    "毕业院校": "graduate_school",
    "毕业学校": "graduate_school",
    "院校": "graduate_school",
    "学历": "education",
    "最高学历": "education",
    "学位": "education",
    "政治面貌": "political_status",
    "出生日期": "birth_date",
    "出生年月": "birth_date",
    "生日": "birth_date",
    "年龄": "age",
    "民族": "ethnicity",
    "籍贯": "native_place",
    "家庭住址": "address",
    "住址": "address",
    "地址": "address",
    "邮箱": "email",
    "电子邮箱": "email",
    "职称": "title",
    "职务": "position",
    "任教学科": "subject",
    "学科": "subject",
    "科目": "subject",
    "入职日期": "hire_date",
    "入职时间": "hire_date",
    "工号": "employee_id",
    "教师编号": "employee_id",
}

# 主表内置字段列表
BUILTIN_FIELDS = {
    "name", "gender", "id_card", "phone", "mobile", "short_phone",
    "birth_date", "age", "graduate_school", "education", "political_status",
    "ethnicity", "native_place", "address", "email", "title", "position",
    "subject", "hire_date", "employee_id", "tags"
}

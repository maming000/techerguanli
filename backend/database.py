"""
数据库初始化与连接管理
"""
import sqlite3
import os
from backend.config import DATABASE_PATH, DATABASE_DIR


def get_connection():
    """获取数据库连接"""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """初始化数据库表结构"""
    conn = get_connection()
    cursor = conn.cursor()

    # 教师主表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gender TEXT,
            id_card TEXT UNIQUE,
            phone TEXT,
            mobile TEXT,
            short_phone TEXT,
            birth_date TEXT,
            age INTEGER,
            graduate_school TEXT,
            education TEXT,
            political_status TEXT,
            ethnicity TEXT,
            native_place TEXT,
            address TEXT,
            email TEXT,
            title TEXT,
            position TEXT,
            subject TEXT,
            hire_date TEXT,
            employee_id TEXT,
            tags TEXT DEFAULT '[]',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 扩展字段表（key-value 结构）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_extra_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
            UNIQUE(teacher_id, field_name)
        )
    """)

    # 字段注册表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS field_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_name TEXT UNIQUE NOT NULL,
            display_name TEXT,
            field_type TEXT DEFAULT 'TEXT',
            is_builtin BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 操作日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS change_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            teacher_name TEXT,
            action TEXT NOT NULL,
            field_name TEXT,
            old_value TEXT,
            new_value TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 用户表（管理员/教师账号）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            teacher_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
        )
    """)

    # 登录会话
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # 教师改动审核请求
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_change_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            requester_user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            reviewer_user_id INTEGER,
            review_note TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            reviewed_at DATETIME,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
            FOREIGN KEY (requester_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (reviewer_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teachers_name ON teachers(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teachers_id_card ON teachers(id_card)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teachers_mobile ON teachers(mobile)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_extra_teacher_id ON teacher_extra_fields(teacher_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_teacher_id ON change_logs(teacher_id)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_teacher_id ON users(teacher_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_change_requests_status ON teacher_change_requests(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_change_requests_teacher_id ON teacher_change_requests(teacher_id)")

    # 初始化内置字段注册
    builtin_fields = [
        ("name", "姓名", "TEXT", 1),
        ("gender", "性别", "TEXT", 1),
        ("id_card", "身份证号", "TEXT", 1),
        ("phone", "联系电话", "TEXT", 1),
        ("mobile", "手机", "TEXT", 1),
        ("short_phone", "小号", "TEXT", 1),
        ("birth_date", "出生日期", "TEXT", 1),
        ("age", "年龄", "INTEGER", 1),
        ("graduate_school", "毕业院校", "TEXT", 1),
        ("education", "学历", "TEXT", 1),
        ("political_status", "政治面貌", "TEXT", 1),
        ("ethnicity", "民族", "TEXT", 1),
        ("native_place", "籍贯", "TEXT", 1),
        ("address", "家庭住址", "TEXT", 1),
        ("email", "邮箱", "TEXT", 1),
        ("title", "职称", "TEXT", 1),
        ("position", "职务", "TEXT", 1),
        ("subject", "任教学科", "TEXT", 1),
        ("hire_date", "入职日期", "TEXT", 1),
        ("employee_id", "工号", "TEXT", 1),
    ]
    for field_name, display_name, field_type, is_builtin in builtin_fields:
        cursor.execute(
            "INSERT OR IGNORE INTO field_registry (field_name, display_name, field_type, is_builtin) VALUES (?, ?, ?, ?)",
            (field_name, display_name, field_type, is_builtin)
        )

    # 初始化默认管理员
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    has_admin = cursor.fetchone()[0] > 0
    if not has_admin:
        from backend.services.auth_utils import hash_password
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
            ("admin", hash_password("admin123"))
        )

    # 初始化默认浏览账号（只读）
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'viewer'")
    has_viewer = cursor.fetchone()[0] > 0
    if not has_viewer:
        from backend.services.auth_utils import hash_password
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'viewer')",
            ("viewer", hash_password("viewer123"))
        )

    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

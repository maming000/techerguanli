import sqlite3
import tempfile
import unittest
import os

from backend.services import data_cleaner


class DataCleanerMergePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

        self.original_get_connection = data_cleaner.get_connection
        self.original_builtin_fields = data_cleaner.BUILTIN_FIELDS
        data_cleaner.get_connection = self.get_connection
        data_cleaner.BUILTIN_FIELDS = {"name", "id_card", "mobile", "education", "tags"}
        self._init_schema()

    def tearDown(self):
        data_cleaner.get_connection = self.original_get_connection
        data_cleaner.BUILTIN_FIELDS = self.original_builtin_fields
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        conn = self.get_connection()
        conn.execute(
            """
            CREATE TABLE teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                id_card TEXT UNIQUE,
                mobile TEXT,
                education TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE teacher_extra_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                field_value TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE change_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER,
                teacher_name TEXT,
                action TEXT,
                field_name TEXT,
                old_value TEXT,
                new_value TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def _insert_teacher(self):
        conn = self.get_connection()
        conn.execute(
            "INSERT INTO teachers (name, id_card, mobile, education, tags, created_at, updated_at) VALUES (?, ?, ?, ?, '[]', '2026-01-01', '2026-01-01')",
            ("张三", "110101199001010011", "13800000000", None),
        )
        conn.commit()
        conn.close()

    def _get_teacher(self):
        conn = self.get_connection()
        row = conn.execute("SELECT * FROM teachers WHERE id_card = ?", ("110101199001010011",)).fetchone()
        conn.close()
        return row

    def test_fill_missing_does_not_overwrite_non_empty_field(self):
        self._insert_teacher()
        stats = data_cleaner.process_records(
            [
                {
                    "name": "张三",
                    "id_card": "110101199001010011",
                    "mobile": "13999999999",
                    "education": "本科",
                }
            ],
            merge_policy="fill_missing",
        )
        self.assertEqual(stats["updated"], 1)
        row = self._get_teacher()
        self.assertEqual(row["mobile"], "13800000000")
        self.assertEqual(row["education"], "本科")

    def test_overwrite_replaces_existing_field(self):
        self._insert_teacher()
        stats = data_cleaner.process_records(
            [{"name": "张三", "id_card": "110101199001010011", "mobile": "13999999999"}],
            merge_policy="overwrite",
        )
        self.assertEqual(stats["updated"], 1)
        row = self._get_teacher()
        self.assertEqual(row["mobile"], "13999999999")

    def test_skip_existing_keeps_record_unchanged(self):
        self._insert_teacher()
        stats = data_cleaner.process_records(
            [{"name": "张三", "id_card": "110101199001010011", "mobile": "13999999999"}],
            merge_policy="skip_existing",
        )
        self.assertEqual(stats["skipped"], 1)
        row = self._get_teacher()
        self.assertEqual(row["mobile"], "13800000000")

    def test_analyze_records_returns_expected_counts(self):
        self._insert_teacher()
        preview = data_cleaner.analyze_records(
            [
                {"name": "张三", "id_card": "110101199001010011", "mobile": "13999999999"},
                {"name": "李四", "id_card": "110101199001010022", "mobile": "13700000000"},
            ],
            merge_policy="skip_existing",
        )
        self.assertEqual(preview["new"], 1)
        self.assertEqual(preview["skipped"], 1)


if __name__ == "__main__":
    unittest.main()

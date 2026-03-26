import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.antigravity_rotator import agv


class RotatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        agv.CONFIG_DIR = base
        agv.CONFIG_PATH = base / "config.yaml"
        agv.STATE_PATH = base / "state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write_config(self, data):
        agv.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        agv.CONFIG_PATH.write_text(json.dumps(data), encoding="utf-8")

    def test_validate_duplicate_accounts(self):
        cfg = {
            "accounts": [
                {"id": "a", "label": "A", "browser": "chrome"},
                {"id": "a", "label": "B", "browser": "chrome"},
            ]
        }
        with self.assertRaises(agv.ConfigError):
            agv.validate_config(cfg)

    def test_validate_missing_accounts(self):
        with self.assertRaises(agv.ConfigError):
            agv.validate_config({"rotation": {"strategy": "round_robin"}})

    def test_select_next_account_round_robin(self):
        accounts = [
            agv.Account("a", "A", "chrome", None, None, None),
            agv.Account("b", "B", "chrome", None, None, None),
        ]
        idx, acc = agv.select_next_account(accounts, -1)
        self.assertEqual(idx, 0)
        self.assertEqual(acc.account_id, "a")
        idx, acc = agv.select_next_account(accounts, idx)
        self.assertEqual(idx, 1)
        self.assertEqual(acc.account_id, "b")
        idx, acc = agv.select_next_account(accounts, idx)
        self.assertEqual(idx, 0)
        self.assertEqual(acc.account_id, "a")

    def test_resolve_workspace_url(self):
        cfg = {"accounts": [], "default_workspace_url": "https://example.com"}
        acc = agv.Account("a", "A", "chrome", None, None, None)
        self.assertEqual(
            agv.resolve_workspace_url(cfg, acc, None), "https://example.com"
        )
        self.assertEqual(
            agv.resolve_workspace_url(cfg, acc, "https://override.com"),
            "https://override.com",
        )

    def test_resolve_workspace_url_missing(self):
        cfg = {"accounts": []}
        acc = agv.Account("a", "A", "chrome", None, None, None)
        with self.assertRaises(agv.ConfigError):
            agv.resolve_workspace_url(cfg, acc, None)

    def test_rotate_fixed_without_default(self):
        cfg = {
            "rotation": {"strategy": "fixed"},
            "accounts": [{"id": "a", "label": "A", "browser": "chrome"}],
        }
        self.write_config(cfg)
        with self.assertRaises(agv.ConfigError):
            agv.cmd_rotate(
                agv.build_parser().parse_args(["rotate", "--dry-run"])
            )

    def test_rotate_dry_run_no_state_change(self):
        cfg = {
            "rotation": {"strategy": "round_robin"},
            "default_workspace_url": "https://example.com",
            "accounts": [
                {"id": "a", "label": "A", "browser": "chrome"},
                {"id": "b", "label": "B", "browser": "chrome"},
            ],
        }
        self.write_config(cfg)
        agv.save_state({"last_index": 0})
        args = agv.build_parser().parse_args(["rotate", "--dry-run"])

        with mock.patch.object(agv, "build_open_command", return_value=["echo"]):
            agv.cmd_rotate(args)

        state = agv.load_state()
        self.assertEqual(state.get("last_index"), 0)


if __name__ == "__main__":
    unittest.main()

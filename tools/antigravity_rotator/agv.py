#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Antigravity multi-account rotator CLI (compliant)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CONFIG_DIR = Path.home() / ".config" / "antigravity-rotator"
CONFIG_PATH = CONFIG_DIR / "config.yaml"
STATE_PATH = CONFIG_DIR / "state.json"

DEFAULT_CONFIG = {
    "version": 1,
    "rotation": {"strategy": "round_robin"},
    "default_workspace_url": None,
    "default_account_id": None,
    "accounts": [],
}


@dataclass
class Account:
    account_id: str
    label: str
    browser: str
    profile: Optional[str]
    workspace_url: Optional[str]
    browser_cmd: Optional[List[str]]


class ConfigError(Exception):
    pass


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_yaml_or_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return json.loads(json.dumps(DEFAULT_CONFIG))

    # JSON is valid YAML 1.2. Prefer YAML if available, otherwise JSON only.
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(raw)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ConfigError("Config root must be a mapping/object.")
        return data
    except ModuleNotFoundError:
        # Fallback: JSON only.
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                "Config file must be JSON (valid YAML 1.2) when PyYAML is not installed."
            ) from exc
        if not isinstance(data, dict):
            raise ConfigError("Config root must be a mapping/object.")
        return data


def _dump_json_as_yaml(path: Path, data: Dict[str, Any]) -> None:
    # Write JSON content (valid YAML 1.2) for zero-dependency config.
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config() -> Dict[str, Any]:
    _ensure_config_dir()
    data = _load_yaml_or_json(CONFIG_PATH)
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    merged.update({k: v for k, v in data.items() if v is not None})
    return merged


def save_config(cfg: Dict[str, Any]) -> None:
    _ensure_config_dir()
    _dump_json_as_yaml(CONFIG_PATH, cfg)


def load_state() -> Dict[str, Any]:
    _ensure_config_dir()
    if not STATE_PATH.exists():
        return {"last_index": -1}
    raw = STATE_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        return {"last_index": -1}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"last_index": -1}
    if not isinstance(data, dict):
        return {"last_index": -1}
    if "last_index" not in data:
        data["last_index"] = -1
    return data


def save_state(state: Dict[str, Any]) -> None:
    _ensure_config_dir()
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_config(cfg: Dict[str, Any]) -> None:
    if "accounts" not in cfg or not isinstance(cfg["accounts"], list):
        raise ConfigError("Config must include 'accounts' list.")

    seen = set()
    for idx, acc in enumerate(cfg["accounts"]):
        if not isinstance(acc, dict):
            raise ConfigError(f"Account at index {idx} must be an object.")
        account_id = acc.get("id")
        if not account_id or not isinstance(account_id, str):
            raise ConfigError(f"Account at index {idx} must have string 'id'.")
        if account_id in seen:
            raise ConfigError(f"Duplicate account id: {account_id}")
        seen.add(account_id)

        label = acc.get("label")
        if not label or not isinstance(label, str):
            raise ConfigError(f"Account {account_id} must have string 'label'.")

        browser = acc.get("browser")
        if not browser or not isinstance(browser, str):
            raise ConfigError(f"Account {account_id} must have string 'browser'.")

        profile = acc.get("profile")
        if profile is not None and not isinstance(profile, str):
            raise ConfigError(f"Account {account_id} 'profile' must be a string if set.")

        workspace_url = acc.get("workspace_url")
        if workspace_url is not None and not isinstance(workspace_url, str):
            raise ConfigError(
                f"Account {account_id} 'workspace_url' must be a string if set."
            )

        browser_cmd = acc.get("browser_cmd")
        if browser_cmd is not None:
            if not isinstance(browser_cmd, list) or not all(
                isinstance(x, str) for x in browser_cmd
            ):
                raise ConfigError(
                    f"Account {account_id} 'browser_cmd' must be a list of strings."
                )

    if "rotation" in cfg and cfg["rotation"] is not None:
        rot = cfg["rotation"]
        if not isinstance(rot, dict):
            raise ConfigError("'rotation' must be an object.")
        strategy = rot.get("strategy", "round_robin")
        if strategy not in {"round_robin", "fixed"}:
            raise ConfigError("rotation.strategy must be 'round_robin' or 'fixed'.")


def accounts_from_config(cfg: Dict[str, Any]) -> List[Account]:
    accounts: List[Account] = []
    for acc in cfg.get("accounts", []):
        accounts.append(
            Account(
                account_id=acc["id"],
                label=acc.get("label", acc["id"]),
                browser=acc.get("browser", "chrome"),
                profile=acc.get("profile"),
                workspace_url=acc.get("workspace_url"),
                browser_cmd=acc.get("browser_cmd"),
            )
        )
    return accounts


def find_account(accounts: List[Account], account_id: str) -> Optional[Tuple[int, Account]]:
    for idx, acc in enumerate(accounts):
        if acc.account_id == account_id:
            return idx, acc
    return None


def select_next_account(accounts: List[Account], last_index: int) -> Tuple[int, Account]:
    if not accounts:
        raise ConfigError("No accounts configured.")
    next_index = (last_index + 1) % len(accounts)
    return next_index, accounts[next_index]


def _platform_browser_cmd(browser: str, profile: Optional[str], url: str) -> List[str]:
    browser = browser.lower()
    profile_arg = f"--profile-directory={profile}" if profile else None

    if sys.platform == "darwin":
        app_map = {
            "chrome": "Google Chrome",
            "edge": "Microsoft Edge",
            "brave": "Brave Browser",
        }
        app_name = app_map.get(browser)
        if not app_name:
            raise ConfigError(f"Unsupported browser '{browser}' on macOS.")
        cmd = ["open", "-a", app_name]
        if profile_arg:
            cmd += ["--args", profile_arg, url]
        else:
            cmd += ["--args", url]
        return cmd

    if sys.platform.startswith("win"):
        exe_map = {
            "chrome": "chrome",
            "edge": "msedge",
            "brave": "brave",
        }
        exe = exe_map.get(browser)
        if not exe:
            raise ConfigError(f"Unsupported browser '{browser}' on Windows.")
        parts = ["cmd", "/c", "start", "", exe]
        if profile_arg:
            parts.append(profile_arg)
        parts.append(url)
        return parts

    # Assume Linux
    bin_map = {
        "chrome": "google-chrome",
        "edge": "microsoft-edge",
        "brave": "brave-browser",
    }
    bin_name = bin_map.get(browser)
    if not bin_name:
        raise ConfigError(f"Unsupported browser '{browser}' on Linux.")
    cmd = [bin_name]
    if profile_arg:
        cmd.append(profile_arg)
    cmd.append(url)
    return cmd


def build_open_command(acc: Account, url: str) -> List[str]:
    if acc.browser_cmd:
        return acc.browser_cmd + [url]
    return _platform_browser_cmd(acc.browser, acc.profile, url)


def resolve_workspace_url(cfg: Dict[str, Any], acc: Account, override_url: Optional[str]) -> str:
    if override_url:
        return override_url
    if acc.workspace_url:
        return acc.workspace_url
    default_url = cfg.get("default_workspace_url")
    if not default_url:
        raise ConfigError(
            "No workspace URL found. Set account workspace_url or config default_workspace_url."
        )
    return default_url


def cmd_add_account(args: argparse.Namespace) -> None:
    cfg = load_config()
    validate_config(cfg)

    if any(acc.get("id") == args.id for acc in cfg["accounts"]):
        raise ConfigError(f"Account id '{args.id}' already exists.")

    account = {
        "id": args.id,
        "label": args.label or args.id,
        "browser": args.browser,
        "profile": args.profile,
        "workspace_url": args.workspace_url,
        "browser_cmd": args.browser_cmd,
    }
    cfg["accounts"].append(account)

    if args.set_default:
        cfg["default_account_id"] = args.id

    save_config(cfg)
    print(f"Added account: {args.id}")


def cmd_list(args: argparse.Namespace) -> None:
    cfg = load_config()
    validate_config(cfg)
    accounts = accounts_from_config(cfg)
    default_id = cfg.get("default_account_id")

    if not accounts:
        print("No accounts configured.")
        return

    print("ID\tLabel\tBrowser\tProfile\tWorkspace URL\tDefault")
    for acc in accounts:
        is_default = "yes" if acc.account_id == default_id else ""
        print(
            f"{acc.account_id}\t{acc.label}\t{acc.browser}\t"
            f"{acc.profile or '-'}\t{acc.workspace_url or '-'}\t{is_default}"
        )


def cmd_set_default(args: argparse.Namespace) -> None:
    cfg = load_config()
    validate_config(cfg)
    accounts = accounts_from_config(cfg)
    if not find_account(accounts, args.id):
        raise ConfigError(f"Account id '{args.id}' not found.")
    cfg["default_account_id"] = args.id
    save_config(cfg)
    print(f"Default account set to: {args.id}")


def _open_account(
    cfg: Dict[str, Any],
    acc: Account,
    dry_run: bool,
    override_url: Optional[str],
) -> None:
    url = resolve_workspace_url(cfg, acc, override_url)
    cmd = build_open_command(acc, url)

    print("Account:", acc.account_id)
    print("Label:", acc.label)
    print("Browser:", acc.browser)
    print("Profile:", acc.profile or "-")
    print("URL:", url)
    print("Command:", " ".join(cmd))

    if dry_run:
        print("Dry run enabled; not opening browser.")
        return

    subprocess.Popen(cmd)


def cmd_open(args: argparse.Namespace) -> None:
    cfg = load_config()
    validate_config(cfg)
    accounts = accounts_from_config(cfg)

    found = find_account(accounts, args.id)
    if not found:
        raise ConfigError(f"Account id '{args.id}' not found.")

    idx, acc = found
    _open_account(cfg, acc, args.dry_run, args.url)

    if not args.dry_run:
        state = load_state()
        state["last_index"] = idx
        save_state(state)


def cmd_rotate(args: argparse.Namespace) -> None:
    cfg = load_config()
    validate_config(cfg)
    accounts = accounts_from_config(cfg)
    state = load_state()
    last_index = int(state.get("last_index", -1))

    strategy = cfg.get("rotation", {}).get("strategy", "round_robin")
    if strategy == "fixed":
        default_id = cfg.get("default_account_id")
        if not default_id:
            raise ConfigError("rotation.strategy is 'fixed' but no default_account_id set.")
        found = find_account(accounts, default_id)
        if not found:
            raise ConfigError(f"Default account '{default_id}' not found.")
        idx, acc = found
    else:
        idx, acc = select_next_account(accounts, last_index)

    _open_account(cfg, acc, args.dry_run, args.url)

    if not args.dry_run:
        state["last_index"] = idx
        save_state(state)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agv",
        description="Antigravity IDE multi-account compliant rotator",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add-account", help="Add a new account")
    p_add.add_argument("--id", required=True, help="Account id (unique)")
    p_add.add_argument("--label", help="Display label")
    p_add.add_argument("--browser", default="chrome", help="Browser: chrome/edge/brave")
    p_add.add_argument("--profile", help="Browser profile directory name")
    p_add.add_argument("--workspace-url", help="Workspace URL for this account")
    p_add.add_argument(
        "--browser-cmd",
        nargs="+",
        help="Custom browser command as a list (overrides browser/profile)",
    )
    p_add.add_argument(
        "--set-default",
        action="store_true",
        help="Set this account as default",
    )
    p_add.set_defaults(func=cmd_add_account)

    p_list = sub.add_parser("list", help="List accounts")
    p_list.set_defaults(func=cmd_list)

    p_set = sub.add_parser("set-default", help="Set default account")
    p_set.add_argument("id", help="Account id")
    p_set.set_defaults(func=cmd_set_default)

    p_open = sub.add_parser("open", help="Open Antigravity IDE for an account")
    p_open.add_argument("id", help="Account id")
    p_open.add_argument("--url", help="Override workspace URL")
    p_open.add_argument("--dry-run", action="store_true", help="Do not open browser")
    p_open.set_defaults(func=cmd_open)

    p_rot = sub.add_parser("rotate", help="Round-robin open next account")
    p_rot.add_argument("--url", help="Override workspace URL")
    p_rot.add_argument("--dry-run", action="store_true", help="Do not open browser")
    p_rot.set_defaults(func=cmd_rotate)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

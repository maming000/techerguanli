# Antigravity Rotator (CLI)

A compliant, local-only CLI for rotating between **authorized** Google accounts and opening the Antigravity IDE/workspace. This tool **does not store passwords** and **does not bypass quotas**.

## Install / Run

Use the repo's Python to run the CLI directly:

```bash
python tools/antigravity_rotator/agv.py --help
```

## Quick Start

```bash
# Add two accounts
python tools/antigravity_rotator/agv.py add-account --id acc-a --label "Account A" --browser chrome --profile "Profile 1" --workspace-url "https://example.com/antigravity"
python tools/antigravity_rotator/agv.py add-account --id acc-b --label "Account B" --browser chrome --profile "Profile 2" --workspace-url "https://example.com/antigravity"

# Round-robin open next account
python tools/antigravity_rotator/agv.py rotate --dry-run
python tools/antigravity_rotator/agv.py rotate

# Open a specific account
python tools/antigravity_rotator/agv.py open acc-a --dry-run
```

## Config Location

Config is stored at:

```
~/.config/antigravity-rotator/config.yaml
```

The file is written as **JSON** (which is valid YAML 1.2), so it works without extra dependencies. Example:

```json
{
  "version": 1,
  "rotation": {"strategy": "round_robin"},
  "default_workspace_url": "https://example.com/antigravity",
  "default_account_id": "acc-a",
  "accounts": [
    {
      "id": "acc-a",
      "label": "Account A",
      "browser": "chrome",
      "profile": "Profile 1",
      "workspace_url": "https://example.com/antigravity"
    },
    {
      "id": "acc-b",
      "label": "Account B",
      "browser": "chrome",
      "profile": "Profile 2"
    }
  ]
}
```

State is stored at:

```
~/.config/antigravity-rotator/state.json
```

## Notes

- You must already be logged into the relevant accounts in the selected browser profiles.
- `rotation.strategy` supports `round_robin` and `fixed`.
- For unsupported browsers or custom launches, you can set `browser_cmd` as a list of command tokens.

## Compliance

This tool is intended for **authorized** accounts and **does not** automate or bypass rate limits, quotas, or access controls.

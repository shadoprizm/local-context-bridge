#!/usr/bin/env python3
"""OpenClaw local skill entrypoint for Local Context Bridge."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).parent / "scripts" / "local_md_linker.py"


def _payload(context: dict[str, Any]) -> dict[str, Any]:
    raw = context.get("pre_instructions") or context.get("payload") or context.get("input") or {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"action": "list", "query": raw.strip()}
    return {"action": "list"}


def run(context: dict[str, Any]) -> dict[str, Any]:
    payload = _payload(context)
    action = payload.get("action", "list")
    cmd = [sys.executable, str(SCRIPT)]
    if payload.get("config"):
        cmd.extend(["--config", str(payload["config"])])
    if payload.get("output_mode"):
        cmd.extend(["--output-mode", str(payload["output_mode"])])

    if action == "init":
        cmd.append("init")
    elif action in {"preflight", "list", "search"}:
        cmd.append("list")
        if payload.get("since_hours") is not None:
            cmd.extend(["--since-hours", str(payload.get("since_hours"))])
        cmd.extend(["--limit", str(payload.get("limit", 25))])
        if payload.get("query"):
            cmd.extend(["--query", str(payload["query"])])
    elif action == "preview":
        cmd.extend(["preview", str(payload["path_id"])])
    elif action in {"pack", "pack_for_chat"}:
        path_ids = payload.get("path_ids") or []
        if not path_ids:
            raise ValueError("pack action requires path_ids")
        cmd.append("pack")
        if payload.get("mode"):
            cmd.extend(["--mode", str(payload["mode"])])
        cmd.extend(map(str, path_ids))
    else:
        raise ValueError(f"Unsupported action: {action}")

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        return {"success": False, "summary": "Local Context Bridge failed", "stderr": proc.stderr, "cmd": cmd}
    data = json.loads(proc.stdout)
    if action == "init":
        summary = f"Initialized config at {data.get('config_path')}"
    elif action in {"preflight", "list", "search"}:
        summary = f"Found {data.get('count', 0)} recent markdown files."
    elif action == "preview":
        summary = f"Previewed {data['file']['title']}"
    else:
        summary = f"Packed {data.get('count', 0)} markdown files for chat."
    return {"success": True, "summary": summary, "result": data}

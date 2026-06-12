from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "local_md_linker.py"
spec = importlib.util.spec_from_file_location("local_md_linker", MODULE_PATH)
assert spec and spec.loader
local_md_linker = importlib.util.module_from_spec(spec)
sys.modules["local_md_linker"] = local_md_linker
spec.loader.exec_module(local_md_linker)


def write_config(tmp_path: Path, root: Path, extra: str = "") -> Path:
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
roots:
  - name: Test Vault
    path: {root}
    type: vault
exclude:
  - .git
  - .env
  - secrets
max_file_kb: 256
default_since_hours: 72
{extra}
""".strip(),
        encoding="utf-8",
    )
    return config


def args(**kwargs):
    base = {
        "config": None,
        "output_mode": "private",
        "since_hours": 999,
        "limit": 25,
        "query": "",
        "path_id": "",
        "path_ids": [],
        "mode": "full",
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_list_extracts_title_tags_and_redacts_absolute_paths_in_public_mode(tmp_path: Path):
    root = tmp_path / "vault"
    root.mkdir()
    note = root / "launch.md"
    note.write_text("---\ntitle: Launch Plan\ntags: launch, agents\n---\n# Ignored\nBody #demo\n", encoding="utf-8")
    config = write_config(tmp_path, root)

    result = local_md_linker.list_recent(args(config=str(config), output_mode="public"))

    assert result["success"] is True
    assert result["count"] == 1
    item = result["files"][0]
    assert item["title"] == "Launch Plan"
    assert item["display_path"] == "launch.md"
    assert item["source"] == "vault"
    assert item["root_name"] == "Test Vault"
    assert "absolute_path" not in item
    assert set(item["tags"]) >= {"launch", "agents", "demo"}


def test_search_matches_title_path_and_tags(tmp_path: Path):
    root = tmp_path / "vault"
    root.mkdir()
    (root / "alpha.md").write_text("# Alpha\n#build\n", encoding="utf-8")
    (root / "beta.md").write_text("# Beta\n", encoding="utf-8")
    config = write_config(tmp_path, root)

    by_tag = local_md_linker.list_recent(args(config=str(config), query="build"))
    by_title = local_md_linker.list_recent(args(config=str(config), query="beta"))

    assert [f["title"] for f in by_tag["files"]] == ["Alpha"]
    assert [f["title"] for f in by_title["files"]] == ["Beta"]


def test_blocked_directories_are_excluded(tmp_path: Path):
    root = tmp_path / "vault"
    (root / ".git").mkdir(parents=True)
    (root / "secrets").mkdir()
    (root / "good").mkdir()
    (root / ".git" / "hidden.md").write_text("# Hidden\n", encoding="utf-8")
    (root / "secrets" / "secret.md").write_text("# Secret\n", encoding="utf-8")
    (root / "good" / "safe.md").write_text("# Safe\n", encoding="utf-8")
    config = write_config(tmp_path, root)

    result = local_md_linker.list_recent(args(config=str(config)))

    assert result["count"] == 1
    assert result["files"][0]["title"] == "Safe"


def test_secret_warning_is_reported(tmp_path: Path):
    root = tmp_path / "vault"
    root.mkdir()
    (root / "note.md").write_text("# Note\napi_key: should-not-be-here\n", encoding="utf-8")
    config = write_config(tmp_path, root)

    result = local_md_linker.list_recent(args(config=str(config)))

    assert result["files"][0]["secret_warning"] is True


def test_metadata_pack_omits_content_and_public_output_omits_absolute_path(tmp_path: Path):
    root = tmp_path / "vault"
    root.mkdir()
    (root / "note.md").write_text("# Note\nPrivate body\n", encoding="utf-8")
    config = write_config(tmp_path, root)
    listed = local_md_linker.list_recent(args(config=str(config)))
    path_id = listed["files"][0]["path_id"]

    result = local_md_linker.pack(args(config=str(config), output_mode="public", mode="metadata", path_ids=[path_id]))

    assert result["success"] is True
    assert result["mode"] == "metadata"
    assert "Private body" not in result["chat_markdown"]
    assert "Metadata-only attachment" in result["chat_markdown"]
    assert "absolute_path" not in result["attachments"][0]["file"]


def test_init_writes_default_config(tmp_path: Path):
    target = tmp_path / "cfg" / "config.yaml"

    result = local_md_linker.write_default_config(str(target))

    assert result["success"] is True
    assert target.exists()
    assert "roots:" in target.read_text(encoding="utf-8")

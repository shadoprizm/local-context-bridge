#!/usr/bin/env python3
"""Safe local Markdown discovery/preview/packaging for channel chat context."""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Iterable

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "local-context-bridge" / "config.yaml"
FALLBACK_ROOTS = [Path.home() / "Documents", Path.home() / "projects", Path.home() / "Sync"]
DEFAULT_BLOCKED_PARTS = {
    ".git", ".ssh", ".gnupg", ".env", ".pytest_cache", "node_modules", ".venv", "venv", "__pycache__",
    "credentials", "secrets", "private_keys", "keys",
}
SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password|private[_-]?key)\b\s*[:=]"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/]+=*"),
]
MAX_PREVIEW_CHARS = 8000
MAX_PACK_CHARS_PER_FILE = 20000


def _expand(p: str | Path) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(p)))).resolve()


def _tiny_yaml(text: str) -> dict:
    """Parse the small config shape without external deps; falls back to JSON if needed."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    data: dict = {}
    current = None
    current_item = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current = line[:-1].strip()
            data[current] = []
            current_item = None
        elif not line.startswith(" ") and ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = _coerce(v.strip())
            current = None
        elif current and line.strip().startswith("-"):
            item = line.strip()[1:].strip()
            if ":" in item:
                k, v = item.split(":", 1)
                current_item = {k.strip(): _coerce(v.strip())}
                data[current].append(current_item)
            else:
                current_item = None
                data[current].append(_coerce(item))
        elif current_item is not None and ":" in line:
            k, v = line.strip().split(":", 1)
            current_item[k.strip()] = _coerce(v.strip())
    return data


def _coerce(v: str):
    v = v.strip().strip('"\'')
    if v.lower() in {"true", "false"}:
        return v.lower() == "true"
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def load_config(path: str | None = None) -> dict:
    cfg_path = _expand(path) if path else DEFAULT_CONFIG_PATH
    if cfg_path.exists():
        cfg = _tiny_yaml(cfg_path.read_text(encoding="utf-8"))
        cfg["_config_path"] = str(cfg_path)
        return cfg
    return {
        "roots": [{"name": p.name or str(p), "path": str(p), "type": "local"} for p in FALLBACK_ROOTS if p.exists()],
        "exclude": sorted(DEFAULT_BLOCKED_PARTS),
        "max_file_kb": 256,
        "default_since_hours": 72,
        "public_mode_default": "metadata",
        "_config_path": None,
    }


def write_default_config(path: str | None = None) -> dict:
    cfg_path = _expand(path) if path else DEFAULT_CONFIG_PATH
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    example = Path(__file__).resolve().parents[1] / "config.example.yaml"
    if example.exists():
        shutil.copyfile(example, cfg_path)
    else:
        cfg_path.write_text("roots:\n  - name: Notes\n    path: ~/Documents\n    type: notes\n", encoding="utf-8")
    return {"success": True, "config_path": str(cfg_path)}


@dataclasses.dataclass
class RootInfo:
    name: str
    path: Path
    type: str = "local"


@dataclasses.dataclass
class MdFile:
    path: Path
    root: RootInfo
    size: int
    mtime: float
    sha256: str
    title: str
    secret_warning: bool
    tags: list[str]

    @property
    def path_id(self) -> str:
        return hashlib.sha256(str(self.path).encode("utf-8")).hexdigest()[:16]

    @property
    def display_path(self) -> str:
        try:
            return str(self.path.relative_to(self.root.path))
        except ValueError:
            return self.path.name

    def as_dict(self, public: bool = False) -> dict:
        d = {
            "path_id": self.path_id,
            "title": self.title,
            "display_path": self.display_path,
            "source": self.root.type,
            "root_name": self.root.name,
            "mtime": dt.datetime.fromtimestamp(self.mtime, tz=dt.timezone.utc).isoformat(),
            "size_bytes": self.size,
            "sha256": self.sha256,
            "secret_warning": self.secret_warning,
            "tags": self.tags,
        }
        if not public:
            d["absolute_path"] = str(self.path)
        return d


def configured_roots(cfg: dict) -> list[RootInfo]:
    out = []
    for item in cfg.get("roots") or []:
        if isinstance(item, str):
            p = _expand(item)
            name, typ = p.name, "local"
        else:
            p = _expand(item.get("path", ""))
            name = str(item.get("name") or p.name or p)
            typ = str(item.get("type") or "local")
        if p.exists() and p.is_dir():
            out.append(RootInfo(name=name, path=p, type=typ))
    return out


def is_blocked(path: Path, blocked_parts: set[str]) -> bool:
    parts = {p.lower() for p in path.parts}
    if parts & blocked_parts:
        return True
    name = path.name.lower()
    return name.startswith(".") or name.endswith(('.key', '.pem', '.crt', '.p12'))


def safe_read(path: Path, limit: int | None = None) -> str:
    data = path.read_text(encoding="utf-8", errors="replace")
    return data[:limit] if limit else data


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def title_from_text(text: str, fallback: str) -> str:
    m = re.search(r"(?im)^title:\s*['\"]?(.+?)['\"]?\s*$", text[:3000])
    if m:
        return m.group(1).strip()[:160]
    m = re.search(r"(?m)^#\s+(.+?)\s*$", text[:5000])
    if m:
        return m.group(1).strip()[:160]
    return fallback.rsplit('.', 1)[0].replace('-', ' ').replace('_', ' ').strip().title()[:160]


def tags_from_text(text: str) -> list[str]:
    tags = set(re.findall(r"(?<!\w)#([A-Za-z0-9_/-]{2,60})", text[:20000]))
    fm = re.search(r"(?ims)^---\s*(.*?)\s*---", text[:5000])
    if fm:
        for m in re.finditer(r"(?im)^tags:\s*(.+)$", fm.group(1)):
            tags.update(t.strip(" []'\"") for t in m.group(1).split(",") if t.strip())
    return sorted(t for t in tags if t)


def has_secret_warning(text: str) -> bool:
    return any(p.search(text) for p in SECRET_PATTERNS)


def iter_markdown_files(cfg: dict) -> Iterable[MdFile]:
    blocked = {str(x).lower() for x in cfg.get("exclude", [])} | DEFAULT_BLOCKED_PARTS
    max_bytes = int(cfg.get("max_file_kb", 256)) * 1024
    for root in configured_roots(cfg):
        for path in root.path.rglob("*.md"):
            try:
                path = path.resolve()
                if is_blocked(path, blocked) or not path.is_file():
                    continue
                stat = path.stat()
                if stat.st_size > max_bytes:
                    continue
                text = safe_read(path, min(20000, max_bytes))
                yield MdFile(path, root, stat.st_size, stat.st_mtime, hash_file(path), title_from_text(text, path.name), has_secret_warning(text), tags_from_text(text))
            except (OSError, UnicodeError):
                continue


def list_recent(args) -> dict:
    cfg = load_config(args.config)
    since = args.since_hours if args.since_hours is not None else float(cfg.get("default_since_hours", 72))
    cutoff = dt.datetime.now().timestamp() - since * 3600
    files = [f for f in iter_markdown_files(cfg) if f.mtime >= cutoff]
    if args.query:
        q = args.query.lower()
        files = [f for f in files if q in f.title.lower() or q in f.display_path.lower() or any(q in t.lower() for t in f.tags)]
    files.sort(key=lambda f: f.mtime, reverse=True)
    public = args.output_mode == "public"
    return {"success": True, "config_path": cfg.get("_config_path"), "count": min(len(files), args.limit), "files": [f.as_dict(public=public) for f in files[:args.limit]]}


def resolve_path_id(path_id: str, cfg: dict) -> MdFile:
    for f in iter_markdown_files(cfg):
        if f.path_id == path_id:
            return f
    raise SystemExit(f"Unknown or no-longer-allowed path_id: {path_id}")


def preview(args) -> dict:
    cfg = load_config(args.config)
    f = resolve_path_id(args.path_id, cfg)
    text = safe_read(f.path, MAX_PREVIEW_CHARS)
    return {"success": True, "file": f.as_dict(public=args.output_mode == "public"), "content_preview": text, "truncated": f.size > len(text.encode('utf-8', errors='replace'))}


def pack(args) -> dict:
    cfg = load_config(args.config)
    packed = []
    total_chars = 0
    public = args.output_mode == "public"
    mode = args.mode
    for pid in args.path_ids:
        f = resolve_path_id(pid, cfg)
        text = "" if mode == "metadata" else safe_read(f.path, MAX_PACK_CHARS_PER_FILE)
        total_chars += len(text)
        packed.append({"file": f.as_dict(public=public), "content": text, "truncated": mode != "metadata" and f.size > len(text.encode('utf-8', errors='replace'))})
    md_parts = ["# Local Markdown Attachments\n"]
    for item in packed:
        meta = item["file"]
        md_parts.append(f"\n## {meta['title']}\n")
        md_parts.append(f"- Source: {meta['source']} / {meta['root_name']}\n- Path: {meta['display_path']}\n- SHA256: {meta['sha256']}\n- Modified UTC: {meta['mtime']}\n- Secret warning: {meta['secret_warning']}\n")
        if meta.get("tags"):
            md_parts.append(f"- Tags: {', '.join(meta['tags'])}\n")
        md_parts.append("\n")
        if mode == "metadata":
            md_parts.append("[Metadata-only attachment: content intentionally omitted.]\n")
        else:
            md_parts.append(item["content"])
        if item["truncated"]:
            md_parts.append("\n\n[TRUNCATED]\n")
    return {"success": True, "count": len(packed), "mode": mode, "output_mode": args.output_mode, "total_chars": total_chars, "attachments": packed, "chat_markdown": "\n".join(md_parts)}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", help="Path to config YAML/JSON. Defaults to ~/.config/local-context-bridge/config.yaml")
    p.add_argument("--output-mode", choices=["private", "public"], default="private", help="public redacts absolute paths")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("init")
    lp = sub.add_parser("list")
    lp.add_argument("--since-hours", type=float, default=None)
    lp.add_argument("--limit", type=int, default=25)
    lp.add_argument("--query", default="")
    pp = sub.add_parser("preview")
    pp.add_argument("path_id")
    pk = sub.add_parser("pack")
    pk.add_argument("--mode", choices=["full", "metadata"], default="full")
    pk.add_argument("path_ids", nargs="+")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.action == "init":
        result = write_default_config(args.config)
    elif args.action == "list":
        result = list_recent(args)
    elif args.action == "preview":
        result = preview(args)
    elif args.action == "pack":
        result = pack(args)
    else:
        parser.error("unknown action")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

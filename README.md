# VaultDrop

Safely attach local Markdown, Obsidian notes, project specs, and agent artifacts to chat agents in Telegram, Discord, CLI, and OpenClaw workflows.

## Why

Your agent chat is empty, but your real context is in local Markdown files. VaultDrop gives agents a safe, operator-selected way to list, preview, and package those files without broad filesystem access or copy/paste walls.

## Quick start

```bash
python3 scripts/local_md_linker.py init
python3 scripts/local_md_linker.py list --since-hours 72 --limit 10
python3 scripts/local_md_linker.py preview <path_id>
python3 scripts/local_md_linker.py pack <path_id> <path_id>
```

For group channels, use public metadata mode:

```bash
python3 scripts/local_md_linker.py --output-mode public pack --mode metadata <path_id>
```

## Channel workflow

1. User: `list recent md files`
2. Agent lists numbered files with `path_id`
3. User: `preview 2` or `attach 1 and 3`
4. Agent packs the chosen files into `chat_markdown` and uses them as context

## Safety

- Configured allowlist roots only
- Sensitive folders blocked by default
- Public mode redacts absolute paths
- Secret-like content gets flagged
- Metadata-only mode for group/public channels

## Demo

See `assets/demo-transcript.md` for a Telegram/Discord-style interaction.

## Config

Default path:

```bash
~/.config/local-context-bridge/config.yaml
```

See `config.example.yaml`.

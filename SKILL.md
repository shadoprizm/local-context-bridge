---
name: local-context-bridge
description: >
  Local-first Markdown context bridge for agent chat channels. Safely list, preview, search,
  and package local Markdown/Obsidian/project notes so Telegram, Discord, CLI, and OpenClaw
  agents can attach the right files without copy/paste or broad filesystem access.
version: 0.2.0
dependencies: []
provides: ["local_markdown_picker", "obsidian_context", "channel_file_picker", "markdown_context_pack"]
---

# Local Context Bridge

## One-line pitch

Safely attach local Markdown, Obsidian notes, specs, and agent artifacts to chat agents in Telegram, Discord, CLI, and OpenClaw workflows.

## Why this exists

Most useful agent context already lives in local files: Obsidian notes, project specs, research briefs, meeting notes, implementation plans, and generated reports. Chat channels are usually isolated from those files, so operators copy/paste walls of Markdown or lose context.

Local Context Bridge gives agents a safe, user-selected way to find and package local Markdown into chat context.

## Target users

- OpenClaw users running agents from Telegram or Discord
- Obsidian users who want local notes available to agents without uploading the whole vault
- Developers who keep specs/plans in Markdown
- Local-first AI users who want provenance, hashes, and safety gates

## Tool interface

Primary executable:

```bash
python3 scripts/local_md_linker.py <command>
```

Convenience wrapper:

```bash
bin/local-context-bridge <command>
```

Commands:

- `init` — write example config to `~/.config/local-context-bridge/config.yaml`
- `list` — list recent or searched Markdown files from configured roots
- `preview <path_id>` — preview one selected file
- `pack <path_id...>` — produce a chat-ready Markdown context bundle

## What it does

- Lists recent `.md` files from configured roots
- Searches by title, path, and tag
- Extracts title from frontmatter or first heading
- Extracts simple tags from frontmatter and `#tags`
- Previews selected files
- Packs selected files into a chat-ready Markdown bundle
- Supports `full` and `metadata` attachment modes
- Supports `private` and `public` output modes; public mode redacts absolute paths
- Flags likely secrets and blocks sensitive directories by default
- Works as a standalone CLI or OpenClaw local skill

## Constraints / not for

Use this for operator-selected local Markdown context. Do not use it for unattended broad filesystem harvesting, secret discovery, exfiltration, or public auto-posting.

## What it intentionally does not do

- It does not require OCC Nexus.
- It does not publish files automatically to public channels.
- It does not scan arbitrary filesystem paths unless the user configures roots.
- It does not bypass secret warnings or blocked folders.

## Quick start

Initialize config:

```bash
python3 scripts/local_md_linker.py init
```

Edit:

```bash
~/.config/local-context-bridge/config.yaml
```

List recent Markdown files:

```bash
python3 scripts/local_md_linker.py list --since-hours 72 --limit 10
```

Search notes:

```bash
python3 scripts/local_md_linker.py list --query cyberlens --since-hours 168
```

Preview one file:

```bash
python3 scripts/local_md_linker.py preview <path_id>
```

Pack files for private agent context:

```bash
python3 scripts/local_md_linker.py pack <path_id> <path_id>
```

Pack metadata only for public/group channels:

```bash
python3 scripts/local_md_linker.py --output-mode public pack --mode metadata <path_id>
```

## Configuration

See `config.example.yaml`.

Default config path:

```bash
~/.config/local-context-bridge/config.yaml
```

Example:

```yaml
roots:
  - name: Obsidian Vault
    path: ~/Documents/Obsidian
    type: vault
  - name: Project Notes
    path: ~/projects
    type: project

exclude:
  - .git
  - .ssh
  - .gnupg
  - .env
  - node_modules
  - .venv
  - venv
  - credentials
  - secrets
  - keys

max_file_kb: 256
default_since_hours: 72
public_mode_default: metadata
```

## Channel pattern: Telegram / Discord

For chat channels without a GUI picker, use a two-step interaction.

### 1. Operator asks for recent files

User:

```text
list recent md files
```

Agent runs:

```bash
python3 scripts/local_md_linker.py --output-mode public list --since-hours 72 --limit 10
```

Agent replies:

```text
Recent Markdown files:

1. Launch Plan
   vault / Obsidian Vault · launches/clawhub-launch.md
   4.3 KB · id: 3cc9dca1b742a2ee

2. Product Spec
   project / Project Notes · local-context-bridge/SPEC.md
   9.1 KB · id: 6a531daf19ab71e7

Reply: preview 1, attach 2, or search <term>.
```

### 2. Operator selects files

User:

```text
attach 1 and 2 as context
```

Agent runs:

```bash
python3 scripts/local_md_linker.py pack 3cc9dca1b742a2ee 6a531daf19ab71e7
```

Then the agent uses `chat_markdown` as context for its next response.

## OpenClaw local skill payloads

### Init config

```json
{"action":"init"}
```

### List recent Markdown

```json
{"action":"list","since_hours":72,"limit":25,"output_mode":"public"}
```

### Search

```json
{"action":"search","query":"proposal","since_hours":168,"limit":10,"output_mode":"public"}
```

### Preview

```json
{"action":"preview","path_id":"abc123...","output_mode":"public"}
```

### Pack selected files for chat

```json
{"action":"pack_for_chat","path_ids":["abc123...","def456..."],"mode":"full","output_mode":"private"}
```

### Metadata-only group-safe pack

```json
{"action":"pack_for_chat","path_ids":["abc123..."],"mode":"metadata","output_mode":"public"}
```

## Safety model

Local Context Bridge uses explicit configured roots and conservative exclusions. It is designed for operator-selected local context, not unattended broad file harvesting.

Default blocked names include:

- `.git`
- `.ssh`
- `.gnupg`
- `.env`
- `node_modules`
- `.venv` / `venv`
- `credentials`
- `secrets`
- `keys`

Safety behaviors:

- `path_id` selection instead of requiring absolute paths in chat
- public mode redacts absolute paths
- secret-like text triggers `secret_warning: true`
- large files are skipped by config limit
- metadata-only mode is available for group channels

## Recommended agent behavior

- In private DMs, it is acceptable to pack full selected files as context after the operator chooses them.
- In group/public channels, default to metadata-only and ask before sending full content.
- Never auto-dump full file contents just because a recent file exists.
- If `secret_warning` is true, summarize the warning and ask before using the content.

## Roadmap

- Fuzzy search / ranking by active conversation terms
- Terminal picker/TUI
- MCP wrapper
- Save chat response back to Markdown
- Optional semantic index over configured roots
- One-command package installer

## Public positioning

Use this ClawHub pitch:

> Local Context Bridge is the missing file picker for agent chats: safely attach local Markdown, Obsidian notes, project specs, and generated reports to Telegram, Discord, CLI, and OpenClaw agents without copy/paste or broad filesystem access.

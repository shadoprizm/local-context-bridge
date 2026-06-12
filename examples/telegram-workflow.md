# Telegram / Discord Workflow Example

## User asks

```text
list recent md files
```

## Agent runs

```bash
python3 scripts/local_md_linker.py --output-mode public list --since-hours 72 --limit 10
```

## Agent replies

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

## User selects

```text
attach 1 and 2 as context
```

## Agent runs

```bash
python3 scripts/local_md_linker.py pack 3cc9dca1b742a2ee 6a531daf19ab71e7
```

The agent uses the returned `chat_markdown` as private context for its answer.

## Group-channel rule

Default to metadata-only in group/public channels unless the operator explicitly asks to send full content:

```bash
python3 scripts/local_md_linker.py --output-mode public pack --mode metadata 3cc9dca1b742a2ee
```

# Demo: Local Context Bridge in a chat channel

```text
User: list recent md files

Agent: Recent Markdown files:

1. Launch Plan
   vault / Obsidian Vault · launches/clawhub-launch.md
   4.3 KB · id: 3cc9dca1b742a2ee

2. Product Spec
   project / Project Notes · local-context-bridge/SPEC.md
   9.1 KB · id: 6a531daf19ab71e7

Reply: preview 1, attach 2, or search <term>.

User: preview 1

Agent: Preview: Launch Plan
- Source: vault / Obsidian Vault
- Path: launches/clawhub-launch.md
- Secret warning: false

# Launch Plan
Ship the skill, post the demo, collect feedback...

User: attach 1 as context

Agent: Attached Launch Plan as private context. What should I do with it?
```

## Why this works well in Telegram/Discord

The user never has to paste a wall of Markdown. The agent shows safe numbered choices, the operator selects the exact files, and the tool packages only those files into context.

---
description: Token tools. /optimize sessions | scan | repeats | draft (offline analysis of your saved chats)
argument-hint: sessions | scan | repeats | draft  [--session ID] [--project text]
allowed-tools: Bash(sh:*)
---
!`sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" claude_optimizer $ARGUMENTS`

Above is the tool output. Answer briefly in English, by mode:
- sessions / scan: which chats should get /compact or be replaced by a fresh session plus /handoff, and which are fine.
- repeats: a plan to turn the repeated instructions into rules (project CLAUDE.md, docs/ai/DESIGN.md or INDEX.md "## Rules"). Ask for approval before writing any file.
- draft: read the drafts in the output folder and propose the final rules files. Ask for approval before writing.
- no argument or an error: show the four modes with one line each.

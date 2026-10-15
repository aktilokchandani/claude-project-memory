---
description: Check whether this project has memory (docs/ai/). Missing, offers /pinit. Ready, shows where to start and offers /resume.
allowed-tools: Bash(sh:*)
---
!`sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" project_memory check`

Above is the check result. Answer in English, max 5 lines:

- First line always: "Folder: <FOLDER>". If the result says NOT A PROJECT, or the user's recent request is clearly about another project, say the wrong folder is open and tell them to open the right one (`code -n "<path>"`), then stop.
- **MEMORY: MISSING**: say this project has no memory yet (docs/ai/). Ask with AskUserQuestion: "Run /pinit now?" with options "Yes, create it" / "Not now". On yes, run the /pinit steps. On no, do nothing.
- **MEMORY: READY**: read only the "Start here" section (or the first section, if named differently) of `docs/ai/STATUS.md`, sum it up in 2 lines, then ask with AskUserQuestion: "Continue from here (/resume)?" with options "Yes, continue" / "No, I have a new task". On yes, run the /resume steps.

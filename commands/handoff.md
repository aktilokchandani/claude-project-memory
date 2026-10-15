---
description: Save where work stopped into docs/ai/ (STATUS, DECISIONS...) before switching account or ending the session.
argument-hint: (optional) note about what to do next
---
Update the project memory in `docs/ai/` from THIS session, so a new session on any account can continue without reading this chat.

Extra note from the user (may be empty): $ARGUMENTS

If `docs/ai/STATUS.md` does not exist, tell the user to run `/pinit` first and stop.

1. See what changed: `git status --short` and `git diff --stat` (if git), plus what was done in this conversation.
2. Update `docs/ai/STATUS.md`:
   - "Start here": the exact next step (what, file and line if known, command to run), including the user's note above.
   - "In progress": unfinished work with the files touched.
   - "Todo": add new items, remove finished ones.
   - "Done (latest 10)": add today's finished items with the date (YYYY-MM-DD); move the oldest beyond 10 to `HISTORY.md`.
   - "Known issues": bugs found but not fixed.
   - Keep STATUS.md under 60 lines. Keep the existing heading names if they differ.
3. Append one line per real decision to `docs/ai/DECISIONS.md`: `YYYY-MM-DD | decision | reason`.
4. Update `ARCHITECTURE.md`, `DESIGN.md`, `DEPLOY.md`, `TESTING.md` or `PLAN.md` only if this session changed those facts. Small edits, no rewrites.
5. If the user repeated an instruction 2+ times this session, add it once as a rule (UI rules in DESIGN.md, others in INDEX.md under `## Rules`).
6. Passwords and keys go only in `SECRETS.local.md`, and only if the user gave them this session.
7. Do not commit.

Finish with 3 lines in English: what was saved, the "Start here" step, and "Now open a new session (any account) and run /pcheck or /resume."

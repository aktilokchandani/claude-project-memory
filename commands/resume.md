---
description: Continue this project from docs/ai/STATUS.md in a fresh session (cheap, no old chat). Use after switching account.
argument-hint: (optional) a new task instead of the saved next step
---
Continue this project from its saved memory, not from an old chat.

New task from the user (may be empty): $ARGUMENTS

1. `docs/ai/INDEX.md` and `docs/ai/STATUS.md` are usually already loaded through CLAUDE.md. Read them only if they are not in context. If `docs/ai/STATUS.md` does not exist, tell the user to run `/pinit` and stop.
2. Run `git status --short` and `git log --oneline -5` (skip if the project has no git).
3. Open other `docs/ai/` files only when the task needs them (DESIGN.md for UI, ARCHITECTURE.md for backend, DEPLOY.md for deploy, TESTING.md for tests). Open `SECRETS.local.md` only when a login or server access is actually needed.
4. Tell the user in max 3 lines, in English: where the project stands and what you will do now.
5. Then do it: the new task above if given, otherwise the "Start here" step (or the first section, if named differently) from STATUS.md.

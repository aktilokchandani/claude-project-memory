---
description: Create this project's memory in docs/ai/ (index, status, architecture, design, deploy, testing...) so any account or fresh session continues cheaply. Run once per project.
argument-hint: (optional) extra notes about the project
allowed-tools: Bash(sh:*)
---
Set up the project memory folder `docs/ai/` in the current project. Goal: any Claude account, in a brand new session, understands the project and continues from where work stopped, by reading only small files instead of an old chat.

Extra notes from the user (may be empty): $ARGUMENTS

## Rules
- Never overwrite an existing file in `docs/ai/`. If files exist, only add the missing ones and list the ones that already existed.
- User history: if `docs/ai/prompts.local.md` does not exist, run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" project_memory backfill --project .` (zero tokens). Do not read that file whole: grep it for URLs, "live", "deploy", "design", "font", "color", "login", "test", "pending", "todo" and use the hits to fill STATUS, DESIGN, DEPLOY and TESTING instead of TBD. Ignore prompts that are clearly about another project.
- If `docs/ai/last-chat.local.md` exists, read it (it is small): it holds the last answers of the previous chat, so use it for "Start here" and "In progress".
- Gather facts cheaply: read `CLAUDE.md`, `AGENTS.md` (and nested ones), `README*`, the dependency file (`requirements.txt`, `package.json`, `composer.json`, `pyproject.toml`...), `.env.example`, `git log --oneline -20`, and a shallow folder listing. Do NOT read `vendor`, `node_modules`, `venv`, `.venv`, `storage`, `media`, `staticfiles`, `dist`, `build`, `.git`.
- Do not duplicate what `AGENTS.md` or `CLAUDE.md` already says. Link to it instead.
- Unknown facts: write `TBD`, never guess.
- Short files, bullet points, plain words. Do not commit anything.

## Files to create in `docs/ai/`
1. `INDEX.md` (max 30 lines): what the project is (2 lines), main folders, a table of the other files with one line each on when to read them, a `## Rules` section, and the line "Credentials are in SECRETS.local.md, read only when needed."
2. `STATUS.md` (max 60 lines), sections exactly: `## Start here` (the single next step: what, which file, which command), `## In progress`, `## Todo`, `## Done (latest 10)` with dates (YYYY-MM-DD), `## Known issues`.
3. `ARCHITECTURE.md`: stack and tools, backend structure, frontend structure, modules (one line each), third party services and APIs (name, purpose, where configured, never keys).
4. `DESIGN.md`: design spec (fonts, colors, spacing, components), frontend rules the user repeats, screen flows as arrow lists (`Login -> Dashboard -> Leads`).
5. `PLAN.md`: goals, milestones, what is planned next.
6. `DECISIONS.md`: one line per decision, `YYYY-MM-DD | decision | reason`, seeded from git log and docs where obvious.
7. `DEPLOY.md`: local URL, live URL(s), how to run locally, how to deploy, post deploy steps. No passwords.
8. `TESTING.md`: how to run tests, test cases, test user names and roles. No passwords.
9. `HISTORY.md`: archive heading only; old "Done" items move here later.
10. `SECRETS.local.md`: template only, headings `Local server`, `Live server / hosting`, `Database`, `Test users`, `Third party`, each `url / user / password: TBD`.

## After creating the files
- Make sure the project `.gitignore` has `docs/ai/*.local.md` (add it if missing, no duplicate line). Skip if the project has no git.
- Append to the project `CLAUDE.md` (create it if missing; skip lines already present) so every session loads only these two small files:
  ```
  @docs/ai/INDEX.md
  @docs/ai/STATUS.md
  ```
  Never import SECRETS.local.md or the other files.
- Report in English: files created, files skipped, and the TBD items the user should fill in.

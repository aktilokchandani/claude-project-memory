# project-memory for Claude Code

**Switch accounts or open a fresh session and keep working exactly where you stopped, without paying to re-read a long chat.**

By **Ashok Kumar**, Software Engineer and AI Engineer, Karachi, Pakistan.

---

## Why

Every prompt in Claude Code sends the whole conversation again. Inside one account that is mostly served from cache. The cache belongs to one account, so after an account switch, or after the cache expires, resuming a long chat costs ~150k to 200k tokens on the very first prompt.

project-memory keeps each project's knowledge in small files inside the project (`docs/ai/`). A new session on any account reads two short files (~2k tokens) instead of the old chat.

| | First prompt after switching account |
|---|---|
| Resume a long chat | ~150k to 200k tokens, uncached |
| Fresh session + project-memory | ~20k to 25k tokens |

## What makes it different

Claude Code already has CLAUDE.md and auto memory. project-memory adds what they do not cover:

- **Multi account handoff**: `/handoff` on one account, `/resume` on another, no chat re-read.
- **Wrong project guard**: stops work when a prompt belongs to a different project than the open folder.
- **History backfill**: rebuilds a project's memory from your old chats, even chats run from the wrong folder.
- **A fixed, small layout**: only INDEX and STATUS load every session; the rest is read on demand.
- **Token tools**: find oversized sessions and the instructions you keep repeating.

## Install

At the prompt of a Claude Code session:

```
/plugin install project-memory --marketplace aktilokchandani/claude-project-memory
```

Answer `y` to add the marketplace, then pick a scope (user scope to have it in every project).

From a shell:

```
claude plugin install project-memory --marketplace aktilokchandani/claude-project-memory
```

In the desktop app: click + next to the prompt box, then Plugins, Add marketplace with `aktilokchandani/claude-project-memory`, then Add plugin.

Requires Python 3.8+ on PATH (`python3`, `python` or `py`). Works on Windows (with Git for Windows), macOS and Linux.

**For teams**: each member installs the plugin once. Commit `docs/ai/*.md` (not `*.local.md`) and everyone, on any account, continues from the same STATUS.

## Daily workflow

1. Open the project folder in your editor, start a **new** session.
2. Type `/pcheck`. It tells you whether to run `/pinit` (first time) or `/resume`.
3. Work as usual. Claude updates `docs/ai/STATUS.md` after each finished task.
4. Stopping mid task or switching account: `/handoff`, switch, new session, `/pcheck`.

## Demo

Real output from a test project (a tiny Vite shop), Claude Code on Windows.

**`/pcheck` in a project without memory**

```
Folder: ...\testproj
This project has no memory yet: docs/ai/ doesn't exist.
Should I run /pinit now to create it?
```

**`/pinit` (then `docs/ai/` holds INDEX, STATUS, ARCHITECTURE, DESIGN, PLAN, DECISIONS, DEPLOY, TESTING, HISTORY, SECRETS.local)**

```
Start here in STATUS.md says to add a cart page and run it with `npm run dev`.
One thing to fix: package.json has a `dev: vite` script, but vite isn't a dependency.
I logged this under Known issues.
TBD items for you to fill in: framework, design tokens, live URL, test users ...
```

**`/resume` in a fresh session**

```
Where it stands: README, package.json and the docs/ai/ memory; no source code yet.
What I'd do next: install vite, build the cart page in src/ (the "Start here" step),
check it with `npm run dev`, then make the first commit.
```

**Wrong project guard** (a prompt about another project's folder)

```
> Messages in D:\ashok\crm\apps\chat are not loading, fix it
Is this prompt meant for this project (`testproj2`), or for `D:\ashok\crm\apps\chat`?
If it's for the chat app, open that folder and run the prompt again there.
```

Claude stopped before touching anything.

## Commands

| Command | When | What it does |
|---|---|---|
| `/pcheck` | start of every session | shows the open folder and whether memory exists; offers `/pinit` or `/resume` |
| `/pinit` | once per project | builds `docs/ai/` from the code, git log and your old prompts; imports INDEX and STATUS into CLAUDE.md |
| `/resume [task]` | after an account switch or in a new session | reads STATUS, says where things stand, continues the next step (or your new task) |
| `/handoff [note]` | before switching account mid task | saves "Start here", in progress, done and decisions |
| `/optimize sessions` | weekly | your real chats with size and advice (optimize, maybe, skip) |
| `/optimize scan` | when sessions feel slow | size per session, which need `/compact` or a fresh start |
| `/optimize repeats [--session ID]` | weekly | instructions you keep repeating, with a plan to turn them into rules |
| `/optimize draft` | after repeats | drafts of rules files from your repeats |

## Automatic (no command)

- **Rules at session start**: Claude knows the memory layout and when to update it.
- **Prompt log**: each prompt goes to `docs/ai/prompts.local.md` (gitignored).
- **Wrong project guard**: a prompt naming another project's folder (or clearly about another site or product) makes Claude ask before doing anything.
- **Memory reminder**: in a project without memory, Claude offers `/pinit` after your first task.
- **Long session warning**: a notice when a session gets big enough that `/compact` or a fresh session is cheaper.

## The memory folder

```
docs/ai/
  INDEX.md          what the project is, which file to read when   (loaded every session)
  STATUS.md         start here, in progress, todo, done             (loaded every session)
  ARCHITECTURE.md   stack, backend, frontend, modules, third party
  DESIGN.md         design spec, UI rules, screen flows
  PLAN.md           goals and next steps
  DECISIONS.md      date | decision | reason
  DEPLOY.md         local and live URLs, deploy steps (no passwords)
  TESTING.md        test cases, test users (no passwords)
  HISTORY.md        older finished work
  SECRETS.local.md  passwords and keys, gitignored, read only when needed
  prompts.local.md  automatic prompt log, gitignored
```

Commit the `docs/ai/*.md` files if your team should share the memory, or keep the whole folder out of git. `*.local.md` files are always gitignored.

## Recover a chat that ran in the wrong folder

```
python "<plugin folder>/scripts/project_memory.py" backfill --project "/path/to/project" --session <chat id>
```

Copies that chat's prompts and its last answers into the project's `docs/ai/`, then run `/pinit` there. Find chat IDs with `/optimize sessions`.

## Privacy

Everything runs locally. The scripts make no network calls and send nothing anywhere; they only read your local Claude Code transcripts and write inside your project.

## License

MIT, see [LICENSE](LICENSE). © 2026 Ashok Kumar.

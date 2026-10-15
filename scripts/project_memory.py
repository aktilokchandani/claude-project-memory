#!/usr/bin/env python3
"""
project_memory.py - per project memory (docs/ai/) for Claude Code. Offline, zero tokens.
Part of the project-memory plugin by Ashok Kumar.

Commands:
  rules      SessionStart hook: prints the memory rules (only inside a project).
  log        UserPromptSubmit hook: appends each prompt to docs/ai/prompts.local.md,
             flags prompts that name a folder outside this project, and once per session
             reminds Claude to create the memory when docs/ai/STATUS.md is missing.
  check      Prints whether this folder's memory is ready (used by /pcheck).
  backfill   Copies the user's old prompts for this project from saved chats into
             docs/ai/prompts.local.md. With --session it takes one chat regardless of
             folder and also saves that chat's last answers to docs/ai/last-chat.local.md.

Examples:
  python project_memory.py check
  python project_memory.py backfill --project .
  python project_memory.py backfill --project /path/to/app --session 1a2b3c4d
"""
import argparse
import glob
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", HOME / ".claude"))
SRC_DIRS = [CONFIG_DIR / "projects"]
LOG_NAME = "prompts.local.md"
MAX_CHARS = 1500
PROJECT_MARKERS = (".git", "CLAUDE.md", "AGENTS.md", "package.json", "composer.json",
                   "requirements.txt", "manage.py", "pyproject.toml", "go.mod", "Cargo.toml",
                   "wp-config.php")
NOISE = ("this session is being continued", "caveat:", "[request interrupted")
LOG_HEAD = "# User prompts (auto log, local only, gitignored)\n\n"

RULES = """Project memory (project-memory plugin) is active for this project: {root}
- Memory lives in docs/ai/. INDEX.md and STATUS.md describe the project and where work stopped; open the other files there only when the task needs them. Open SECRETS.local.md only when a login or server access is needed.
- Every prompt is logged by a hook to docs/ai/prompts.local.md. Never read it whole; grep it when you need the user's history.
- {missing}
- After every finished task (not every prompt) update docs/ai/STATUS.md: "Start here", "In progress", "Done (latest 10)" with the date. Add a DECISIONS.md line for real decisions. Small edits, no rewrite, no commit, at most one short line about it in your reply.
- When the user repeats an instruction, add it once as a rule (UI rules in DESIGN.md, others in INDEX.md under "## Rules").
- New facts (URLs, deploy steps, test users) go to DEPLOY.md / TESTING.md. Passwords and keys only in SECRETS.local.md.
- Wrong project guard: if a prompt is clearly about a different project than this folder (another folder path, another site or domain, another product's features), do not start. Ask in one short line, in English, whether it is for this project, and wait.
- Everything this plugin makes you say or write (questions, reports, docs/ai files) is in English."""


def project_root(cwd):
    """Walk up from cwd to the project root (.git or a marker file). The home folder is never a project."""
    if not cwd:
        return None
    p = Path(cwd).resolve()
    for cand in [p, *p.parents]:
        if cand == HOME or cand == cand.parent:
            break
        if (cand / ".git").exists():
            return cand
    if p != HOME and any((p / m).exists() for m in PROJECT_MARKERS):
        return p
    return None


def clean(text):
    if not isinstance(text, str):
        return ""
    t = text.strip()
    if not t or t.startswith("<") or t.lower().startswith(NOISE):
        return ""
    if "continued from a previous conversation" in t[:400].lower():
        return ""
    t = " ".join(t.split())
    return t if len(t) <= MAX_CHARS else t[:MAX_CHARS] + " ...(cut)"


PATH_RE = re.compile(r"(?:(?<![A-Za-z0-9])[A-Za-z]:[\\/](?!/)|~/|/(?:home|Users|var/www|srv|opt)/)[^\s\"'<>|*?`]+")


def other_project_paths(prompt, root):
    """Folder paths in the prompt that are outside this project (Claude config and temp folders excluded)."""
    if not isinstance(prompt, str):
        return []
    r = str(root).lower().replace("\\", "/").rstrip("/")
    home = str(HOME).lower().replace("\\", "/")
    out = []
    for m in PATH_RE.findall(prompt):
        raw = m.rstrip(".,;:)]")
        p = raw.replace("\\", "/").lower()
        if p.startswith("~/"):
            p = home + p[1:]
        if p == r or p.startswith(r + "/") or r.startswith(p) or home.startswith(p):
            continue  # this project, a parent of it, or the home folder cut short at a space
        if p.startswith(home + "/.claude") or p.startswith(home + "/appdata") or "/tmp/" in p:
            continue
        out.append(raw)
    return out


def ensure_memory_dir(root):
    d = root / "docs" / "ai"
    d.mkdir(parents=True, exist_ok=True)
    gi = root / ".gitignore"
    if (root / ".git").exists():
        line = "docs/ai/*.local.md"
        try:
            cur = gi.read_text(encoding="utf-8", errors="ignore") if gi.exists() else ""
            if line not in cur.splitlines():
                with open(gi, "a", encoding="utf-8") as f:
                    f.write(("\n" if cur and not cur.endswith("\n") else "") +
                            "\n# Project memory (local only)\n" + line + "\n")
        except OSError:
            pass
    return d


def log_file(root):
    f = ensure_memory_dir(root) / LOG_NAME
    if not f.exists():
        f.write_text(LOG_HEAD, encoding="utf-8")
    return f


def read_stdin():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def cmd_rules(a):
    data = read_stdin()
    root = project_root(data.get("cwd") or os.getcwd())
    if not root:
        return
    if (root / "docs" / "ai" / "STATUS.md").exists():
        missing = "Memory is ready. If the user's first message is vague, suggest /resume."
    else:
        missing = ("Memory is NOT set up yet (no docs/ai/STATUS.md). Do the user's task first, "
                   "then offer to run /pinit to create it.")
    print(RULES.format(root=root, missing=missing))


def cmd_log(a):
    data = read_stdin()
    root = project_root(data.get("cwd") or os.getcwd())
    if not root:
        return
    raw = data.get("prompt", "")
    text = clean(raw)
    sid = (data.get("session_id") or "")[:8]
    foreign = other_project_paths(raw, root)
    if text:
        tag = " [OTHER PROJECT?]" if foreign else ""
        try:
            with open(log_file(root), "a", encoding="utf-8") as f:
                f.write(f"- {datetime.now():%Y-%m-%d %H:%M} [{sid}]{tag} {text}\n")
        except OSError:
            pass
    if foreign:
        print(f"Possible wrong project: this prompt mentions {', '.join(foreign[:3])}, which is "
              f"outside the current project {root}. Before doing ANY work or writing project memory, "
              "ask the user in one short line, in English, to confirm the prompt is for this "
              "project. If not, do nothing and tell them to open that folder instead.")
    if not (root / "docs" / "ai" / "STATUS.md").exists():
        mark = Path(tempfile.gettempdir()) / f"project_memory_hint_{sid or 'x'}"
        if not mark.exists():
            try:
                mark.write_text("1")
            except OSError:
                pass
            print("Project memory missing: this project has no docs/ai/STATUS.md. Do the user's task "
                  "first; at the end offer to run /pinit (docs/ai/prompts.local.md holds the user's history).")


def cmd_check(a):
    root = project_root(os.getcwd()) or Path(os.getcwd()).resolve()
    d = root / "docs" / "ai"
    print(f"FOLDER: {root}")
    if root == HOME:
        print("MEMORY: NOT A PROJECT (home folder)")
        return
    if (d / "STATUS.md").exists():
        print("MEMORY: READY")
        print("FILES: " + ", ".join(sorted(p.name for p in d.glob("*.md"))))
    else:
        print("MEMORY: MISSING")
        if d.exists():
            print("FILES: " + (", ".join(sorted(p.name for p in d.glob("*.md"))) or "(empty)"))


def iter_transcripts():
    files = []
    for src in SRC_DIRS:
        files += glob.glob(os.path.join(str(src), "**", "*.jsonl"), recursive=True)
    return [f for f in files if not Path(f).stem.startswith("agent-")]


def user_text(d):
    c = (d.get("message") or {}).get("content")
    if isinstance(c, list):
        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return c


def cmd_backfill(a):
    root = project_root(a.project) or Path(a.project).resolve()
    key = str(root).lower()
    seen, rows = set(), []
    for path in iter_transcripts():
        if a.session and not Path(path).stem.lower().startswith(a.session.lower()):
            continue
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    if d.get("type") != "user" or d.get("isMeta") or d.get("isCompactSummary"):
                        continue
                    if not a.session:
                        cwd = (d.get("cwd") or "").lower()
                        if not cwd or not (cwd == key or cwd.startswith(key + os.sep)):
                            continue
                    t = clean(user_text(d))
                    if not t or t in seen:
                        continue
                    seen.add(t)
                    ts = (d.get("timestamp") or "")[:16].replace("T", " ")
                    rows.append((ts, (d.get("sessionId") or "")[:8], t))
        except OSError:
            continue
    rows.sort()
    f = log_file(root)
    existing = f.read_text(encoding="utf-8", errors="ignore")
    body = existing[len(LOG_HEAD):] if existing.startswith(LOG_HEAD) else existing
    body = body.replace("## Live log\n", "").lstrip("\n")
    old = "".join(f"- {ts} [{sid}] {t}\n" for ts, sid, t in rows if t not in existing)
    f.write_text(LOG_HEAD + "## Old chats (backfill)\n" + old + "\n## Live log\n" + body,
                 encoding="utf-8")
    print(f"{root}: {len(rows)} unique prompts from old chats -> {f}")
    if a.session:
        write_last_chat(root, a.session)


def write_last_chat(root, session, n=8):
    """The last N Claude answers (text only) of one chat -> docs/ai/last-chat.local.md."""
    files = [p for p in iter_transcripts() if Path(p).stem.lower().startswith(session.lower())]
    if not files:
        return
    path = max(files, key=os.path.getsize)
    turns = []
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("type") != "assistant":
                continue
            c = user_text(d)
            if isinstance(c, str) and len(c.strip()) > 40:
                turns.append(((d.get("timestamp") or "")[:16].replace("T", " "), c.strip()[:3000]))
    out = ensure_memory_dir(root) / "last-chat.local.md"
    body = "\n\n".join(f"### {ts}\n{t}" for ts, t in turns[-n:])
    out.write_text(f"# Last chat {session}: last {min(n, len(turns))} Claude answers (local only)\n\n"
                   + body + "\n", encoding="utf-8")
    print(f"Last answers -> {out}")


def main():
    ap = argparse.ArgumentParser(description="Project memory helper (offline)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("rules"); p.set_defaults(fn=cmd_rules)
    p = sub.add_parser("log"); p.set_defaults(fn=cmd_log)
    p = sub.add_parser("check"); p.set_defaults(fn=cmd_check)
    p = sub.add_parser("backfill"); p.add_argument("--project", default=os.getcwd())
    p.add_argument("--session", default=None,
                   help="only this chat (first characters of its ID), whatever folder it ran in")
    p.set_defaults(fn=cmd_backfill)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

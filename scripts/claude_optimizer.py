#!/usr/bin/env python3
"""
claude_optimizer.py - Claude Code token tools (offline, no API calls, zero tokens).
Part of the project-memory plugin by Ashok Kumar.

Commands:
  sessions  Your real chats (numbered): date, prompts, first prompt, whether to optimize
  scan      Session sizes and what to do (/compact or a fresh session)
  repeats   Prompts you repeat (in a project or in one chat)
  draft     Drafts of CLAUDE.md / DESIGN.md / skills from your repeats
  hook      UserPromptSubmit hook (warns on long sessions and repeated prompts)
  hook-config   Prints the hook snippet for settings.json
  ignore-config settings.json snippet that stops Claude reading heavy folders

Filters (scan / repeats / draft):
  --project <text>   project folder name contains this text
  --session <id>     first characters of a chat ID (see the sessions command)

Examples:
  python claude_optimizer.py sessions
  python claude_optimizer.py repeats --session 1a2b3c4d --min 2
  python claude_optimizer.py draft --session 1a2b3c4d --out draft_one_chat
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------- settings
DEFAULT_SRC = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / "projects"
WARN_TOKENS = 120_000      # above this, suggest /compact
BIG_TOKENS = 300_000       # above this, a fresh session is cheaper
SIMILARITY = 0.45          # how similar two prompts must be to count as the same

# Category -> keywords
CATEGORIES = {
    "ui-consistency": ["font", "alignment", "align", "button", "buttons", "input", "design",
                       "theme", "ui", "color", "colors", "colour", "contrast", "background",
                       "spacing", "padding", "margin", "responsive", "icon", "sidebar",
                       "dropdown", "dashboard", "hero", "viewport", "professional"],
    "forms-popups-motion": ["form", "forms", "popup", "popups", "modal", "animation", "animate",
                            "hover", "smooth", "scroll", "signup", "fields", "attractive"],
    "alerts-and-tables": ["alert", "alerts", "toast", "notification", "table", "tables",
                          "pagination"],
    "copy-reference-section": ["reference", "copy", "duplicate", "exact", "clone", "same as"],
    "db-optimize": ["database", "db", "migration", "index", "query", "queries", "n+1",
                    "optimize", "optimise", "foreign", "relation", "seeder"],
    "module-complete": ["module", "complete", "crud", "validation", "test",
                        "feature", "resource"],
    "workflow-deploy": ["deploy", "ssh", "scp", "live", "server", "changes", "list", "fixes",
                        "push", "release"],
}

STOP = set("the a an is are to of in on for and or it this that with from as at be by "
           "do make please can you me my we our".split())

# Text that is not a prompt the user wrote; ignored
NOISE_PREFIXES = (
    "this session is being continued",
    "caveat:",
    "[request interrupted",
    "session continued",
)


def is_noise(text):
    low = text.lower().lstrip()
    if low.startswith(NOISE_PREFIXES):
        return True
    return "continued from a previous conversation" in low[:400]


# ---------------------------------------------------------------- reading sessions
def extract_user_prompts(path):
    """Only the prompts the user typed, from one .jsonl session."""
    prompts = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") != "user" or d.get("isMeta") or d.get("isCompactSummary"):
                    continue
                c = (d.get("message") or {}).get("content")
                if isinstance(c, list):
                    c = " ".join(x.get("text", "") for x in c
                                 if isinstance(x, dict) and x.get("type") == "text")
                if isinstance(c, str):
                    c = c.strip()
                    # system reminders / slash command wrappers skip
                    if c and not c.startswith("<") and not is_noise(c):
                        prompts.append(c)
    except OSError:
        pass
    return prompts


def project_of(path, src):
    """The project folder of a session file (first part below src)."""
    try:
        rel = os.path.relpath(path, str(src))
    except ValueError:
        return "?"
    parts = Path(rel).parts
    return parts[0] if len(parts) > 1 else "?"


def collect_sessions(src, project=None, session=None, agents=False):
    """(unique sessions, number of duplicate copies).
    - agent-* (subagent) files are hidden by default
    - a session id found in several folders keeps only its largest, newest copy"""
    files = glob.glob(os.path.join(str(src), "**", "*.jsonl"), recursive=True)
    if not agents:
        files = [f for f in files if not Path(f).stem.startswith("agent-")]
    if project:
        p = project.lower()
        files = [f for f in files if p in project_of(f, src).lower()]
    if session:
        s = session.lower()
        files = [f for f in files if Path(f).stem.lower().startswith(s)]
    best = {}
    owners = defaultdict(set)          # session id -> every folder holding a copy
    for f in files:
        key = Path(f).stem
        owners[key].add(project_of(f, src))
        cur = best.get(key)
        if cur is None:
            best[key] = f
            continue
        a = (os.path.getsize(f), os.path.getmtime(f))
        b = (os.path.getsize(cur), os.path.getmtime(cur))
        if a > b:
            best[key] = f
    uniq = sorted(best.values(), key=os.path.getmtime, reverse=True)
    collect_sessions.owners = owners
    return uniq, len(files) - len(uniq)


def find_sessions(src, project=None, session=None, agents=False):
    return collect_sessions(src, project, session, agents)[0]


def est_tokens_from_file(path):
    try:
        return os.path.getsize(path) // 4      # rough: 4 chars ~ 1 token
    except OSError:
        return 0


# ---------------------------------------------------------------- similarity
def words(text):
    ws = re.findall(r"[a-zA-Z0-9؀-ۿ+]+", text.lower())
    return {w for w in ws if len(w) > 2 and w not in STOP}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster(items, threshold=SIMILARITY, cap=4000):
    """Greedy clustering. items: list of (text, project, session_id)."""
    clusters = []
    for text, proj, sid in items[-cap:]:
        w = words(text)
        if len(w) < 3:
            continue
        best, best_s = None, 0.0
        for c in clusters:
            s = jaccard(w, c["words"])
            if s > best_s:
                best, best_s = c, s
        if best is not None and best_s >= threshold:
            best["items"].append(text)
            best["words"] |= w
            best["projects"].add(proj)
            best["sessions"].add(sid)
            if len(text) < len(best["rep"]):
                best["rep"] = text
        else:
            clusters.append({"rep": text, "words": set(w), "items": [text],
                             "projects": {proj}, "sessions": {sid}})
    clusters.sort(key=lambda c: len(c["items"]), reverse=True)
    return clusters


def load_all_prompts(src, project=None, session=None):
    """[(text, project, session_id)], oldest sessions first, duplicates once."""
    out = []
    sessions = find_sessions(src, project, session)
    owners = getattr(collect_sessions, "owners", {})
    for s in reversed(sessions):
        sid = Path(s).stem
        proj = "+".join(sorted(owners.get(sid) or {project_of(s, src)}))
        for t in extract_user_prompts(s):
            out.append((t, proj, sid))
    return out


def short(text, n=140):
    t = " ".join(text.split())
    return t if len(t) <= n else t[: n - 1] + "..."


def short_proj(name, n=34):
    return name if len(name) <= n else "..." + name[-(n - 3):]


def proj_label(c):
    return ", ".join(sorted(short_proj(p) for p in c["projects"]))


def filter_note(a):
    bits = []
    if getattr(a, "project", None):
        bits.append(f"project={a.project}")
    if getattr(a, "session", None):
        bits.append(f"session={a.session}")
    return (" | filter: " + ", ".join(bits)) if bits else ""


# ---------------------------------------------------------------- commands
def cmd_sessions(a):
    sessions, dups = collect_sessions(a.src, a.project)
    rows = []
    for s in sessions:
        ps = extract_user_prompts(s)
        if len(ps) >= a.min_prompts:
            rows.append((s, ps))
    if not rows:
        print(f"No chats with at least {a.min_prompts} prompts found: {a.src}")
        return
    print(f"{'#':>3}  {'LAST ACTIVE':<16} {'PROMPTS':>7} {'TOKENS~':>11}  {'ID':<8}  {'ADVICE':<9} FIRST PROMPT")
    for i, (s, ps) in enumerate(rows[: a.top], 1):
        when = datetime.fromtimestamp(os.path.getmtime(s)).strftime("%Y-%m-%d %H:%M")
        n = len(ps)
        rec = "OPTIMIZE" if n >= 30 else ("maybe" if n >= 10 else "skip")
        print(f"{i:>3}  {when:<16} {n:>7} {est_tokens_from_file(s):>11,}  "
              f"{Path(s).stem[:8]:<8}  {rec:<9} {short(ps[0], 60)}")
    print(f"\nReal chats: {len(rows)} (subagent files hidden, duplicate copies ignored: {dups})")
    print("ADVICE: OPTIMIZE = 30+ prompts (many repeats likely), maybe = 10-29, skip = short chat.")
    print("\nTo optimize one chat (the first 8 characters of the ID are enough):")
    print("  /optimize repeats --session <ID> --min 2")
    print("  /optimize draft --session <ID> --out draft_<ID>")


def cmd_scan(a):
    sessions, dups = collect_sessions(a.src, a.project, a.session, a.agents)
    if not sessions:
        print(f"No sessions found: {a.src}")
        return
    print(f"{'TOKENS~':>9}  {'PROMPTS':>7}  {'ACTION':<13} PROJECT / SESSION")
    total = 0
    for s in sessions[: a.top]:
        t = est_tokens_from_file(s)
        total += t
        n = len(extract_user_prompts(s))
        if t >= BIG_TOKENS:
            act = "NEW SESSION"
        elif t >= WARN_TOKENS:
            act = "/compact"
        else:
            act = "ok"
        print(f"{t:>9,}  {n:>7}  {act:<13} {short_proj(project_of(s, a.src))} / {Path(s).stem[:8]}")
    print(f"\nUnique sessions: {len(sessions)} | duplicate copies ignored: {dups}")
    print(f"Total (top {min(a.top, len(sessions))}): ~{total:,} tokens "
          f"(estimated from file size; the live context after /compact is much smaller)")
    print("Tip: run `sessions` for a clean list of your real chats.")


def cmd_repeats(a):
    items = load_all_prompts(a.src, a.project, a.session)
    sessions, dups = collect_sessions(a.src, a.project, a.session)
    print(f"Unique sessions: {len(sessions)} (duplicate copies ignored: {dups}) | "
          f"prompts: {len(items)}{filter_note(a)}")
    cl = [c for c in cluster(items) if len(c["items"]) >= a.min]
    if not cl:
        print(f"No prompt was repeated {a.min}+ times.")
        return
    for i, c in enumerate(cl[: a.top], 1):
        print(f"\n#{i}  {len(c['items'])} times, {len(c['sessions'])} session(s)")
        print(f"   projects: {proj_label(c)}")
        print(f"   {short(c['rep'], 200)}")


def categorize(text):
    t = text.lower()
    hits = []
    for cat, kws in CATEGORIES.items():
        score = sum(1 for k in kws if re.search(r"\b" + re.escape(k) + r"\b", t))
        if score:
            hits.append((score, cat))
    hits.sort(reverse=True)
    return [c for _, c in hits[:2]]


def cmd_draft(a):
    items = load_all_prompts(a.src, a.project, a.session)
    cl = [c for c in cluster(items) if len(c["items"]) >= a.min]
    by_cat = defaultdict(list)
    for c in cl:
        for cat in categorize(c["rep"] + " " + " ".join(c["items"][:3])):
            by_cat[cat].append(c)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    claude_lines = ["# Project rules (DRAFT, ask Claude to polish)", ""]
    if not a.project and not a.session:
        claude_lines += ["NOTE: several projects or chats are mixed. Use --project or --session "
                         "for a separate draft each.", ""]
    for cat, cs in by_cat.items():
        claude_lines.append(f"## {cat}")
        for c in cs[:6]:
            claude_lines.append(f"- ({len(c['items'])}x, {len(c['sessions'])} sessions) "
                                f"{short(c['rep'], 160)}")
        claude_lines.append("")
        sk = out / "skills" / cat
        sk.mkdir(parents=True, exist_ok=True)
        body = [
            "---",
            f"name: {cat}",
            f"description: Use when the task involves {cat.replace('-', ' ')}. "
            "Follows the user's repeated instructions as one clear checklist.",
            "---",
            "",
            f"# {cat}",
            "",
            "## Instructions the user repeated (evidence)",
        ]
        for c in cs[:10]:
            body.append(f"- ({len(c['items'])}x) {short(c['rep'], 220)}")
        body += ["", "## Steps", "1. (Ask Claude to turn this list into a clear checklist)", ""]
        (sk / "SKILL.md").write_text("\n".join(body), encoding="utf-8")

    (out / "CLAUDE.draft.md").write_text("\n".join(claude_lines), encoding="utf-8")
    design = ["# DESIGN.md (DRAFT)", "",
              "Write the exact values for fonts, colors, contrast, spacing, buttons, inputs, alerts and tables here.",
              "", "## Found in your prompts"]
    for c in by_cat.get("ui-consistency", []) + by_cat.get("forms-popups-motion", []) \
            + by_cat.get("alerts-and-tables", []):
        design.append(f"- {short(c['rep'], 160)}")
    (out / "DESIGN.draft.md").write_text("\n".join(design), encoding="utf-8")

    print(f"Drafts written: {out.resolve()}{filter_note(a)}")
    print("Next: open a new Claude session and say:")
    print(f'  "Read the drafts in {out}/ and turn them into a final CLAUDE.md (max 40 lines), DESIGN.md '
          'and skills. Show me the plan first."')


def cmd_hook(a):
    """UserPromptSubmit hook: reads the hook JSON from stdin."""
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    prompt = data.get("prompt", "")
    tp = data.get("transcript_path")
    msgs = []
    if tp and os.path.exists(tp):
        t = est_tokens_from_file(tp)
        if t >= BIG_TOKENS:
            msgs.append(f"Session is ~{t:,} tokens. Cheaper: /handoff, then a fresh session with /resume.")
        elif t >= WARN_TOKENS:
            msgs.append(f"Session is ~{t:,} tokens. Time for /compact.")
        prev = extract_user_prompts(tp)
        w = words(prompt)
        if len(w) >= 4:
            for p in prev[-40:]:
                if jaccard(w, words(p)) >= 0.7:
                    msgs.append("You gave this prompt before. Make it a rule in CLAUDE.md or docs/ai "
                                "so you never have to repeat it.")
                    break
    if len(prompt) > 4000:
        msgs.append("Very long prompt. Paste only the relevant part (top of the error, the file name), or give a file path.")
    if msgs:
        print(json.dumps({"systemMessage": " | ".join(msgs)}, ensure_ascii=False))


def cmd_hook_config(a):
    script = os.path.abspath(__file__)
    snippet = {"hooks": {"UserPromptSubmit": [{"hooks": [
        {"type": "command", "command": f'python "{script}" hook'}]}]}}
    print("Merge this into each account's settings.json (not needed when the plugin is installed):\n")
    print(json.dumps(snippet, indent=2))


LARAVEL_DENY = ["vendor", "node_modules", "storage", "bootstrap/cache", "public/build",
                "public/vendor", ".git", "dist", "build", "coverage"]
DJANGO_DENY = ["venv", ".venv", "env", "node_modules", "staticfiles", "media", "__pycache__",
               ".git", "dist", "build"]
WP_DENY = ["wp-admin", "wp-includes", "wp-content/uploads", "wp-content/cache",
           "wp-content/upgrade", "node_modules", ".git"]


def cmd_ignore_config(a):
    """Stop Claude reading heavy folders (saves tokens)."""
    presets = {"laravel": LARAVEL_DENY, "django": DJANGO_DENY, "wordpress": WP_DENY}
    folders = presets[a.preset]
    deny = [f"Read(./{f}/**)" for f in folders]
    snippet = {"permissions": {"deny": deny}}
    print(f"Add this to the project's .claude/settings.json (preset: {a.preset}):\n")
    print(json.dumps(snippet, indent=2))
    print("\nNote: when Claude must read a file in one of these folders (a vendor package, say), "
          "remove that rule for the moment.")


def main():
    ap = argparse.ArgumentParser(description="Claude Code token optimizer (offline)")
    ap.add_argument("--src", default=str(DEFAULT_SRC), help="sessions folder (.claude/projects)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_filters(p, session=True):
        p.add_argument("--project", default=None,
                       help="only projects whose folder name contains this text")
        if session:
            p.add_argument("--session", default=None,
                           help="only the chat whose ID starts with these characters")

    p = sub.add_parser("sessions")
    p.add_argument("--top", type=int, default=25)
    p.add_argument("--min-prompts", type=int, default=3, dest="min_prompts")
    add_filters(p, session=False); p.set_defaults(fn=cmd_sessions)
    p = sub.add_parser("scan"); p.add_argument("--top", type=int, default=30)
    p.add_argument("--agents", action="store_true", help="also show subagent files")
    add_filters(p); p.set_defaults(fn=cmd_scan)
    # "repeat" works too
    p = sub.add_parser("repeats", aliases=["repeat"]); p.add_argument("--min", type=int, default=3)
    p.add_argument("--top", type=int, default=30); add_filters(p); p.set_defaults(fn=cmd_repeats)
    p = sub.add_parser("draft"); p.add_argument("--min", type=int, default=2)
    p.add_argument("--out", default="draft_output"); add_filters(p); p.set_defaults(fn=cmd_draft)
    p = sub.add_parser("hook"); p.set_defaults(fn=cmd_hook)
    p = sub.add_parser("hook-config"); p.set_defaults(fn=cmd_hook_config)
    p = sub.add_parser("ignore-config")
    p.add_argument("--preset", choices=["laravel", "django", "wordpress"], default="laravel")
    p.set_defaults(fn=cmd_ignore_config)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

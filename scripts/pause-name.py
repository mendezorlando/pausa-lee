#!/usr/bin/env python3
"""Prints the file name of the /pausa handoff, derived from the title of the
current conversation plus today's date: `Title-2026-08-24.md`.

The date is in the name so that a thread paused over several days leaves one
handoff per day instead of overwriting the previous one. When a thread has
several, /lee lists them with their date and the user chooses.

The title is not in the model's context: it lives in the transcript, in
`{"type":"custom-title","customTitle":...}` records and their twin
`ai-title`. The current session is identified by CLAUDE_CODE_SESSION_ID,
which Claude Code exports to the Bash environment.

Always exits 0 and always prints one line. If it cannot resolve the title it
prints UNKNOWN, so the command decides instead of writing a file with an
invented name.
"""
import os, sys, json, re, glob, time, subprocess, importlib.util
from datetime import datetime

MAX = 49          # 60 minus the date suffix
DATE = re.compile(r"-\d{4}-\d{2}-\d{2}$")
ROOT = os.path.expanduser("~/.claude/projects")
LIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "list-handoffs.py")
WAIT = 1.5         # s: how long to wait for the session's .jsonl to appear
INTERVAL = 0.05
SESSIONS = os.path.expanduser("~/.claude/sessions")
UUID = re.compile(r"[0-9a-fA-F-]{36}")


def slug(s):
    s = s.strip().replace("/", "-").replace("\\", "-")
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^\w.\-]", "", s, flags=re.UNICODE)
    s = re.sub(r"-{2,}", "-", s).strip("-._")
    if s.lower().endswith(".md"):
        s = s[:-3].strip("-._")
    s = DATE.sub("", s)   # if the title already carries a date, don't repeat it
    return s[:MAX].strip("-._")


def _sid_from_process():
    """The sessionId, found by walking up the process tree, or "".

    Claude Code writes `~/.claude/sessions/<pid>.json` with `{sessionId, cwd,
    entrypoint, ...}` as soon as the process starts, long before the
    conversation's `.jsonl` exists. We walk up OUR parents until we reach the
    process that launched us, so this identifies rather than guesses: the
    ancestry only leads to our own Claude.

    It is needed because `CLAUDE_CODE_SESSION_ID` does not always reach a
    command's `!` injection. On 26/08/2026 three /lee runs in a row from other
    conversations said «the session could not be identified» while their
    `.jsonl` was on disk: without the variable there was nowhere to start.
    """
    pid = os.getpid()
    for _ in range(8):
        try:
            with open(os.path.join(SESSIONS, f"{pid}.json"), encoding="utf-8") as f:
                sid = json.load(f).get("sessionId")
            if isinstance(sid, str) and UUID.fullmatch(sid):
                return sid
        except Exception:
            pass
        try:
            r = subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)],
                               capture_output=True, text=True, timeout=2)
            pid = int(r.stdout.strip())
        except Exception:
            return ""
        if pid <= 1:
            return ""
    return ""


def session():
    """The id of THIS session: the environment variable if set, the tree if not."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    return sid if UUID.fullmatch(sid or "") else _sid_from_process()


def transcript(sid=None):
    """The .jsonl of THIS session, or None. Never another session's.

    There used to be a fallback here that returned the project's most recent
    .jsonl, and it was a trap. On the first turn the session's own file takes
    a few tenths of a second to appear, and the fallback then handed over the
    PREVIOUS session's file, with its title. On 26/08/2026 one session —«Token
    waste audit»— opened the handoff of «Hotel booking system» because of it,
    without asking, since /lee with HANDOFFS: 1 does not ask. A minute earlier
    another session had resolved correctly: same input, different result,
    which is exactly what looked like erratic behaviour.

    Against the race we wait for the file, which takes tenths of a second.
    With no identifiable session we return None: /lee lists everything and
    /pausa writes UNKNOWN. Staying silent is right; guessing someone else's
    thread is not.
    """
    sid = sid or session()
    if not sid:
        return None
    pattern = os.path.join(ROOT, "*", sid + ".jsonl")
    deadline = time.time() + WAIT
    while True:
        hits = glob.glob(pattern)
        if hits:
            return hits[0]
        if time.time() >= deadline:
            return None
        time.sleep(INTERVAL)


def title(path):
    custom = ai = ""
    with open(path, errors="replace") as f:
        for l in f:
            if '"custom-title"' not in l and '"ai-title"' not in l:
                continue
            try:
                d = json.loads(l)
            except Exception:
                continue
            if d.get("customTitle"):
                custom = d["customTitle"]
            elif d.get("aiTitle"):
                ai = d["aiTitle"]
    return custom or ai


def folder(t):
    """The folder this thread already lives in, or "" for the working directory.

    A thread moves by taking its handoffs along: if its handoffs are in
    OPTIMIZATION/, the next /pausa writes there too. The thread's most recent
    handoff decides, not the best-scoring one, because during a move there are
    handoffs of the same thread in both folders.

    Reuses the matcher in list-handoffs.py so that "same thread" means the
    same in /pausa and in /lee. The import is in here and not at the top:
    list-handoffs imports this module, and at module level they would bite
    each other's tail.
    """
    try:
        spec = importlib.util.spec_from_file_location("list_handoffs", LIST)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        data = {}
        for f in m.candidates():
            ok, h1 = m.analyze(f)
            if ok:
                data[f] = h1
        thread = m.of_thread(t, sorted(data, key=m.mtime, reverse=True), data)
        return os.path.dirname(max(thread, key=m.mtime)) if thread else ""
    except Exception:
        return ""


def main():
    try:
        p = transcript()
        t = title(p) if p else ""
        s = slug(t)
    except Exception:
        t = s = ""
    if not s:
        print("UNKNOWN")
        return
    today = datetime.now().strftime("%Y-%m-%d")
    print(os.path.join(folder(t), f"{s}-{today}.md"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # The docstring promises "always prints one line". If none comes out,
        # /pausa is left with an empty NAME FROM CONVERSATION, which is neither
        # UNKNOWN nor a path: the branch nobody wrote.
        print("UNKNOWN")

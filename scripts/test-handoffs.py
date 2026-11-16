#!/usr/bin/env python3
"""Regression suite for /lee and /pausa. Run it after touching any of
list-handoffs.py, pause-name.py or prune-handoffs.py.

Works in a temporary directory and under a HOME of its own; removes both at
the end and never looks at or touches the real working directory. Exits with
1 if anything fails.

Covers: the three /lee counts, matching by title and by H1, the three causes
of not matching, that another session's title is NEVER inherited (the
26/08/2026 bug), subfolders, trash in both cases, the per-thread cap, the
handoff signature, the slug, folder inheritance and the four guarantees of
pruning.
"""
import os, sys, json, shutil, subprocess, tempfile

REAL = os.path.expanduser("~")
BIN = os.path.dirname(os.path.abspath(__file__))
SAND = tempfile.mkdtemp(prefix="rev-lee-")
# A HOME of its own. The scripts resolve `~/.claude/...` with expanduser, so
# under this HOME they read and write ONLY here. Until 26/08/2026 this suite
# created a fake project inside ~/.claude/projects: touching the app's real
# state to test it is exactly what must not be done, and if the process died
# halfway it stayed there.
HOME = tempfile.mkdtemp(prefix="rev-home-")
PROJ = os.path.join(HOME, ".claude", "projects", "-tests")
os.makedirs(PROJ)
SECS = "\n".join(f"## {s}" for s in
                 ("Decided", "Touched", "In progress", "Next step", "Do not repeat"))
failures = []


def handoff(rel, h1, secs=SECS, mtime=None):
    p = os.path.join(SAND, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(f"# {h1}\n\n{secs}\n")
    if mtime:
        os.utime(p, (mtime, mtime))
    return p


def session(sid, title):
    with open(os.path.join(PROJ, sid + ".jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "sessionId": sid}) + "\n")
        if title is not None:
            f.write(json.dumps({"type": "custom-title", "sessionId": sid,
                                "customTitle": title}) + "\n")


def run(script, sid="", extra=None, home=None):
    """By default, a HOME of its own: without `~/.claude/sessions` there is no
    process tree to walk, so «no session» is truly simulated and nothing of
    the app is touched. `home=REAL` is for the one case that needs the real
    HOME: checking that the pid fallback finds the live session. Even then it
    only reads."""
    env = dict(os.environ)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env["HOME"] = home or HOME
    if sid:
        env["CLAUDE_CODE_SESSION_ID"] = sid
    if extra:
        env.update(extra)
    r = subprocess.run([sys.executable, os.path.join(BIN, script)],
                       cwd=SAND, env=env, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def check(n, cond, detail=""):
    print(f"  {'ok ' if cond else 'FAIL'}  {n}")
    if not cond:
        failures.append(n)
        if detail:
            print("        " + detail.replace("\n", "\n        "))


SID_A = "aaaaaaaa-1111-2222-3333-444444444444"   # «Token waste audit»
SID_B = "bbbbbbbb-1111-2222-3333-444444444444"   # «Hotel booking system»
SID_C = "cccccccc-1111-2222-3333-444444444444"   # no title (first turn)
session(SID_A, "Token waste audit")
session(SID_B, "Hotel booking system")
session(SID_C, None)

print("\n== /lee: count and matching ==")
c, o, e = run("list-handoffs.py", SID_A)
check("0 handoffs -> HANDOFFS: 0", o.startswith("HANDOFFS: 0"), o)

handoff("Token-waste-audit-2026-08-24.md", "Token waste audit", mtime=1000)
# With ONE handoff /lee used to open blindly: without checking the title, it
# handed it to any thread. Closed on 26/08/2026; these four cases are the lock.
c, o, e = run("list-handoffs.py", SID_A)
check("1 handoff, matching title -> opens it and says why",
      o.startswith("HANDOFFS: 1") and "chosen by the conversation title" in o, o)
c, o, e = run("list-handoffs.py", SID_B)
check("1 FOREIGN handoff -> does NOT open it",
      "is NOT from this thread" in o and "chosen by the conversation title" not in o
      and "Open it by the path" not in o, o)
c, o, e = run("list-handoffs.py", SID_C)
check("1 handoff, first turn without title -> opens with a warning",
      "its thread could not be verified" in o
      and "Open it unless" in o, o)
c, o, e = run("list-handoffs.py", "")
check("1 handoff, no session -> opens with a warning",
      o.startswith("HANDOFFS: 1") and "Open it unless" in o, o)

handoff("STATUS.md", "STATUS — Hotel Booking System", mtime=2000)
c, o, e = run("list-handoffs.py", SID_A)
check("2 from different threads, title A -> picks A's",
      o.startswith("HANDOFFS: 1") and "Token" in o and "chosen by the conversation title" in o, o)
c, o, e = run("list-handoffs.py", SID_B)
check("same pair, title B -> picks STATUS.md",
      o.startswith("HANDOFFS: 1") and "STATUS.md" in o, o)

print("\n== /lee: the three causes of not matching ==")
c, o, e = run("list-handoffs.py", SID_C)
check("first turn (no title) -> lists everything + invites to repeat",
      o.startswith("HANDOFFS: 2") and "is not written yet" in o
      and "Run /lee again" in o, o)
c, o, e = run("list-handoffs.py", "")
check("no session -> lists everything + says it cannot identify it",
      o.startswith("HANDOFFS: 2") and "the session could not be identified" in o
      and "Run /lee again" not in o, o)
session("dddddddd-1111-2222-3333-444444444444", "Payment gateway")
c, o, e = run("list-handoffs.py", "dddddddd-1111-2222-3333-444444444444")
check("title that matches nothing -> says so and does not guess",
      o.startswith("HANDOFFS: 2") and "matches none of these" in o, o)

print("\n== /lee: never returns another session's thread ==")
c, o, e = run("list-handoffs.py", "99999999-1111-2222-3333-444444444444")
check("valid sid without transcript -> does NOT inherit a foreign title",
      "chosen by the conversation title" not in o and o.startswith("HANDOFFS: 2"), o)
c, o, e = run("list-handoffs.py", home=REAL)
check("no variable but with a tree -> does not inherit a foreign title either",
      "chosen by the conversation title" not in o, o)

print("\n== /lee: per-thread cap ==")
for i, d in enumerate(("21", "22", "23", "25")):
    handoff(f"Token-waste-audit-2026-08-{d}.md", "Token waste audit", mtime=3000 + i)
c, o, e = run("list-handoffs.py", SID_A)
check("5 of the thread -> lists only the newest and opens it",
      o.startswith("HANDOFFS: 1") and "chosen by the conversation title" in o, o)
check("5 of the thread -> tail with the 4 left behind",
      "(+4 older in the folder)" in o, o)

print("\n== /lee: subfolders and trash ==")
handoff("OPTIMIZATION/Token-waste-audit-2026-08-26.md", "Token waste audit", mtime=9000)
c, o, e = run("list-handoffs.py", SID_A)
check("handoff in a subfolder -> comes out with its prefix",
      "OPTIMIZATION/Token-waste-audit-2026-08-26.md" in o, o)
handoff("trash/Token-old.md", "Token waste audit", mtime=8000)
c, o, e = run("list-handoffs.py", SID_A)
check("trash/ excluded", "trash/" not in o, o)
handoff("Trash/Token-old2.md", "Token waste audit", mtime=8001)
c, o, e = run("list-handoffs.py", SID_A)
check("Trash/ capitalized also excluded", "Trash/" not in o, o)
handoff("a/b/Token-deep.md", "Token waste audit", mtime=8002)
c, o, e = run("list-handoffs.py", SID_A)
check("two levels deep are NOT listed", "a/b/" not in o, o)

print("\n== /lee: grouping when there is no match ==")
c, o, e = run("list-handoffs.py", SID_C)
heads = [l for l in o.splitlines() if l.startswith("— ")]
reads = [l for l in o.splitlines() if l.startswith("Read ")]
n = int(o.splitlines()[0].split(":")[1])
check("several threads -> one header per thread, no line lost or repeated",
      len(heads) >= 2 and len(reads) == n, f"n={n} heads={len(heads)} reads={len(reads)}\n{o}")
check("the Read lines stay intact for pasting",
      all(l.startswith("Read ") and "continue from the next step" in l
          for l in reads), o)
check("each header comes before its own lines",
      o.index("— Token waste audit")
      < o.index("Read OPTIMIZATION/"), o)

print("\n== /lee: handoff detection ==")
open(os.path.join(SAND, "no-handoff.md"), "w").write("# Something\n\n## Decided\n")
c, o, e = run("list-handoffs.py", SID_A)
check("a .md with 1 section does not count as a handoff", "no-handoff" not in o, o)
handoff("old-numbered.md", "Old numbered scheme",
        "\n".join(f"## {i}. {s}" for i, s in enumerate(
            ("Decided", "Touched", "In progress", "Next step"), 1)), mtime=7000)
c, o, e = run("list-handoffs.py", "dddddddd-1111-2222-3333-444444444444")
check("old numbered scheme (4 of 5) does count", "old-numbered.md" in o, o)

print("\n== /lee: tail of what is left behind ==")
SID_E = "eeee0000-1111-2222-3333-444444444444"
session(SID_E, "Dry dock logbook")
handoff("Dry-dock-logbook-2026-08-20.md", "Dry dock logbook", mtime=6000)
c, o, e = run("list-handoffs.py", SID_E)
check("thread with only one -> no tail",
      o.startswith("HANDOFFS: 1") and "older in the folder" not in o, o)
handoff("Dry-dock-logbook-2026-08-21.md", "Dry dock logbook", mtime=6001)
c, o, e = run("list-handoffs.py", SID_E)
check("thread with two -> «+1 older»",
      "(+1 older in the folder)" in o, o)
check("and opens the newest, where it used to ask",
      "2026-08-21" in o and "chosen by the conversation title" in o, o)

print("\n== robustness: never without a number, never a traceback ==")
c, o, e = run("list-handoffs.py", SID_A, {"PYTHONHASHSEED": "0"})
check("exit 0 and a HANDOFFS line", c == 0 and "HANDOFFS:" in o, f"rc={c} err={e}")
r = subprocess.run([sys.executable, "-c", f'''
import importlib.util as u, os, sys
os.chdir({SAND!r})
s=u.spec_from_file_location("lh", {os.path.join(BIN,"list-handoffs.py")!r})
m=u.module_from_spec(s); s.loader.exec_module(m)
orig=m.candidates
m.candidates=lambda: orig()+["GHOST.md"]
oa=m.analyze
m.analyze=lambda r:(True,"x") if r=="GHOST.md" else oa(r)
m.main()
'''], capture_output=True, text=True)
check("ghost file -> does not crash and there is still a number",
      r.returncode == 0 and "HANDOFFS:" in r.stdout, r.stdout + r.stderr)
r = subprocess.run([sys.executable, "-c", f'''
import runpy, sys, os
os.chdir({SAND!r})
import importlib.util as u
s=u.spec_from_file_location("lh", {os.path.join(BIN,"list-handoffs.py")!r})
m=u.module_from_spec(s); s.loader.exec_module(m)
m.candidates=lambda: (_ for _ in ()).throw(RuntimeError("boom"))
try:
    m.main()
except Exception as ex:
    print("HANDOFFS: 0"); print(f"(could not list: {{type(ex).__name__}})")
'''], capture_output=True, text=True)
check("hard failure -> the __main__ guard prints a number",
      "HANDOFFS: 0" in r.stdout, r.stdout + r.stderr)

print("\n== /pausa: name and folder ==")
c, o, e = run("pause-name.py", SID_A)
check("inherits the folder of the thread's newest handoff",
      o.startswith("OPTIMIZATION/Token-waste-audit-"), o)
c, o, e = run("pause-name.py", "")
check("no session -> bare UNKNOWN, not a path", o == "UNKNOWN", o)
c, o, e = run("pause-name.py", home=REAL)
check("no variable but with a tree -> identifies the session anyway",
      o != "UNKNOWN" and o.endswith(".md"), o)
c, o, e = run("pause-name.py", SID_C)
check("first turn -> UNKNOWN, does not invent a name", o == "UNKNOWN", o)
c, o, e = run("pause-name.py", SID_B)
check("thread B -> root folder (its handoff is in the root)",
      "/" not in o and o.startswith("Hotel-booking"), o)

print("\n== /pausa: slug ==")
for title, expected in (
        ("With / slash and \\ backslash", "With-slash-and-backslash"),
        ("Title with accents é and ñ", "Title-with-accents-é-and-ñ"),
        ("Already has a date 2026-08-24", "Already-has-a-date"),
        ("A" * 90, "A" * 49)):
    sid = "eeeeeeee-1111-2222-3333-44444444444" + str(len(title) % 10)
    session(sid, title)
    c, o, e = run("pause-name.py", sid)
    base = os.path.basename(o)
    check(f"slug of «{title[:28]}»",
          base.startswith(expected) and base.endswith(".md")
          and len(base) <= 63 and "/" not in base and o != "UNKNOWN",
          f"-> {o!r}")

print("\n== pruning ==")
c, o, e = run("prune-handoffs.py", "")
check("no title -> prunes nothing", "nothing pruned" in o, o + e)
before = sorted(os.listdir(os.path.join(SAND, "OPTIMIZATION")))
c, o, e = run("prune-handoffs.py", SID_B)
check("thread B (1 handoff) -> does not touch A's",
      sorted(os.listdir(os.path.join(SAND, "OPTIMIZATION"))) == before, o + e)
c, o, e = run("prune-handoffs.py", SID_A)
alive = [f for f in os.listdir(SAND) if f.endswith(".md") and "Token" in f]
alive += ["OPTIMIZATION/" + f for f in os.listdir(os.path.join(SAND, "OPTIMIZATION"))
          if f.endswith(".md")]
check("pruning leaves 2 of the thread, the current one and its predecessor",
      len(alive) == 2, f"{o}\nalive={alive}")
check("the retired ones go to trash next to their file",
      os.path.isdir(os.path.join(SAND, "trash")), o)
c2, o2, e2 = run("prune-handoffs.py", SID_A)
check("pruning is idempotent", "under the maximum" in o2, o2 + e2)
check("STATUS.md (another thread) is still there",
      os.path.exists(os.path.join(SAND, "STATUS.md")))

shutil.rmtree(SAND, ignore_errors=True)
shutil.rmtree(HOME, ignore_errors=True)
print("\n" + ("ALL GREEN" if not failures else f"FAILURES: {len(failures)} -> {failures}"))
sys.exit(1 if failures else 0)

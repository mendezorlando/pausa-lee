#!/usr/bin/env python3
"""Lists the /pausa handoffs in the working directory, or opens this
thread's directly when the title identifies it.

A .md counts as a handoff if it has at least 4 of the 5 sections /pausa
writes. Numbered ("## 1. Decided") and unnumbered ("## Decided") headings
are both accepted.

Prints the content of no file: only the name, already built into the
instruction ready to copy and paste. Sorted newest first. Always exits 0.
"""
import os, re, glob, unicodedata, importlib.util
from datetime import datetime

PAUSE_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pause-name.py")
THRESHOLD = 0.6    # minimum overlap title <-> name or H1
NEAR_EXACT = 0.9   # with a single specific word in common, demand near identity
# Words that match by chance: they are no proof of kinship.
VAGUE = {"analysis", "status", "notes", "session", "project", "work",
         "summary", "audit", "report"}
STOPWORDS = {"the", "and", "for", "with", "from", "that", "this", "into",
             "about", "between", "over", "its", "our", "your", "are", "was"}


NO_TITLE = ("the conversation title is not written yet; on the first message "
            "of a session it arrives a few seconds later")
NO_SESSION = ("the session could not be identified, so there is no title to "
              "match against")
# Telling them apart matters: NO_TITLE is fixed by repeating and NO_SESSION is
# not, and until 26/08/2026 the second showed up in cases that were the first.


def title_and_reason():
    """(title, reason), reusing pause-name.py. Survives /clear: the new
    session inherits the title (sometimes reworded).

    The reason is only filled when the title comes out empty, and tells the
    two causes apart: the first turn, fixed by repeating, and the
    unidentifiable session, which is not. Before, both looked the same —a long
    list with no explanation— and read as if the matcher had gone mad.
    """
    try:
        spec = importlib.util.spec_from_file_location("pause_name", PAUSE_NAME)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        sid = m.session()
        if not sid:
            return "", NO_SESSION
        path = m.transcript(sid)
        if not path:
            # We know who we are; the transcript is not written yet. It is the
            # first turn, not an unidentified session.
            return "", NO_TITLE
        t = m.title(path)
        return (t, "") if t else ("", NO_TITLE)
    except Exception:
        return "", NO_SESSION


def current_title():
    """Just the title. Used by prune-handoffs.py, which prunes nothing on ""."""
    return title_and_reason()[0]


def words(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9]+", s)
            if len(w) > 2 and w not in STOPWORDS and not w.isdigit()}


def of_thread(t, paths, h1s):
    """This thread's handoffs, best first; [] if there is no clear one.

    After /clear the title may come back reworded ("Hotel booking system" ->
    "Analysis of the hotel booking system"), so equality will not do: overlap
    is measured within the shorter one. Each file is scored against its name
    and against its H1, and the better of the two wins. Two specific words in
    common are required (or a single one if the rest of the title matches
    almost entirely), so that a bare "Status" or "Audit" does not match other
    threads. On a tie, list: picking the wrong thread costs more than a
    question. If more than one comes out, all are listed: with the date in the
    name, a thread paused over several days has one handoff per day, and
    choosing which to resume is the user's call, not the matcher's.

    Renaming the conversation loosens the match in proportion to what is lost
    from the title; there is no thread identifier underneath to fall back on,
    because the sessionId changes with /clear and so does the bridgeSessionId.
    The next /pausa rewrites the name and resyncs it."""
    tw = words(t)
    if len(tw) < 2:
        return []
    scored = []
    for r in paths:
        best = 0.0
        for cand in (os.path.splitext(os.path.basename(r))[0], h1s.get(r, "")):
            pw = words(cand)
            if not pw:
                continue
            common = tw & pw
            specific = len(common - VAGUE)
            if specific < 1:
                continue
            s = len(common) / min(len(tw), len(pw))
            # A single specific word only counts if otherwise they are the
            # same title: "Token audit" yes, "Security audit" no.
            if specific < 2 and s < NEAR_EXACT:
                continue
            best = max(best, s)
        if best >= THRESHOLD:
            scored.append((best, r))
    scored.sort(reverse=True)
    return [r for _, r in scored]


SECTIONS = ("Decided", "Touched", "In progress", "Next step", "Do not repeat")
HEADER = re.compile(
    r"^#{1,3}\s*(?:\d+[.)]\s*)?(" + "|".join(SECTIONS) + r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)
H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
MINIMUM = 4    # of 5, to tolerate a trimmed handoff
MAX = 20       # ceiling of the listing, in case the directory fills up


EXCLUDED = {"trash"}           # what pruning retired is never listed again
LEVELS = ("*.md", "*/*.md")    # the directory and one level of subfolders


def candidates():
    """The .md files of the directory and of one level of subfolders.

    A thread can move to its own folder taking its handoffs along
    (`OPTIMIZATION/`, for instance); without this /lee would stop seeing them.
    What keeps any stray .md in a subfolder from passing as a handoff is not
    this function, it is the section filter in analyze().
    """
    seen = set()
    for pattern in LEVELS:
        for r in glob.glob(pattern):
            if os.path.dirname(r).lower() not in EXCLUDED:
                seen.add(r)
    return sorted(seen)


def analyze(path):
    """(is_handoff, document_title), reading the file only once.

    The H1 matters as much as the name: a handoff named `STATUS.md` says
    nothing about its thread in its name, but its first line does —
    `# STATUS — Hotel Booking System`."""
    try:
        if os.path.getsize(path) > 2_000_000:
            return False, ""
        with open(path, errors="replace") as f:
            txt = f.read()
    except Exception:
        return False, ""
    ok = len({m.group(1).lower() for m in HEADER.finditer(txt)}) >= MINIMUM
    m = H1.search(txt)
    return ok, (m.group(1) if m else "")


def mtime(path):
    """0.0 if the file is gone. Used to sort and to date: a .md can vanish
    between candidates() and here, and a bare getmtime brought the whole
    script down -- leaving /lee without its HANDOFFS: line."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def date(path):
    t = mtime(path)
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M") if t else "no date"


def line(path, behind=0):
    # The tail counts what is still in the folder and no longer listed. It
    # goes after the date on purpose: the line is copied and pasted as a
    # prompt, and the date is exactly where the user already cuts it.
    tail = f" (+{behind} older in the folder)" if behind else ""
    return f"Read {path} and continue from the next step. — {date(path)}{tail}"


def key(r, h1s):
    """A handoff's thread: its H1, or its name if it has none."""
    return h1s.get(r) or os.path.basename(r)


def one_per_thread(paths, h1s):
    """(the most recent of each thread, how many each thread leaves behind).

    The old ones are neither deleted nor hidden: they stay in the folder, open
    by name, and pruning archives them at its own pace. They only leave the
    LISTING, which is the only thing that costs tokens. Measured on
    26/08/2026: each line is 120 characters ~ 55 tok re-read on every later
    turn (48 turns median), and the two old lines of one thread were ~5.2k per
    session that nobody ever opened -- zero reads of a superseded handoff in
    24 sessions. On top of that, three lines of the same thread blocked the
    branch that opens on its own, which requires len(of_thread_) == 1: pruning
    punished the most active thread.
    """
    seen, newest, behind = set(), [], {}
    for r in paths:            # already newest to oldest
        k = key(r, h1s)
        if k in seen:
            behind[k] = behind.get(k, 0) + 1
        else:
            seen.add(k)
            newest.append(r)
    return newest, behind


def group(paths, h1s):
    """[(thread_name, [paths])], threads by their most recent handoff.

    Only for when no match was possible: on the first message of a session
    that always happens, and a flat list of six handoffs from three threads
    reads as a jumble. Grouped it is a menu, and the thread's name is also the
    word that works for `/lee <word>`.

    Groups by the document's H1, which is what says which thread it belongs
    to; without one, each file goes alone under its own name. Does not reorder
    within a group: still newest to oldest.
    """
    groups = {}
    for r in paths:
        groups.setdefault(key(r, h1s), []).append(r)
    if len(groups) < 2:
        return [("", list(paths))]   # a single thread: the header adds nothing
    return list(groups.items())      # dict keeps insertion order


# The instructions live here and not in lee.md because lee.md is injected
# WHOLE on every /lee -- all five branches, when only one applies -- and stays
# in the transcript, re-read on every later call. Measured on 26/08/2026: /lee
# is typed first and has a median of 48 turns ahead (mean 69, max 413).
# Emitting only the branch that fired is the same useful text paid once
# instead of five times per turn.
# Literalness is stated ONCE and shared. `several` had it and `loose` did not,
# and `loose` is the branch that fires on EVERY first message with more than
# one thread: without the clause the model formats the list -- bullets,
# backticks, headings -- and drops the "Read ... and continue from the next
# step." along the way, which is exactly what makes the line pasteable as the
# next prompt. Seen on 26/08/2026 in two sessions, with two different
# formattings, so the instruction was missing, not the model at fault. Shared
# so the branches do not drift apart again.
LITERAL = ("exactly as they come, whole and one per line, no comments and no "
           "reordering: each line is the prompt the user will copy")

INSTR = {
    "zero": "No handoffs here: say so in one line and stop.",
    "failure": "The search FAILED. Say that, not that there are no handoffs: they are not the same.",
    "one": "Open it by the path exactly as given, folder included. In three lines at most, tell the user where things stand, then keep working from its «Next step» section without asking for confirmation.",
    "one_title": "Name the file in those three lines: it was chosen by the conversation title, so a wrong thread shows at once.",
    "only": "It is the only handoff in the folder and its thread could not be verified. Open it unless this conversation's history says it is about something else; if it does, do not open it: say so in one line and stop.",
    "foreign": "The only handoff in the folder is NOT from this thread: the conversation title, which is written, says so. Do not open it and do not summarize it; say so in one line and stop, unless the user asks you to open it anyway.",
    "several": f"Print those lines {LITERAL}. Do not open any file: the user chooses.",
    "loose": f"The dash lines group by thread; print them {LITERAL}. Which thread you are could not be determined, but this conversation's history does say, and that is the one thing this listing cannot see. If it tells you WITHOUT DOUBT: print only its group and what you base that on, and if a single line is left, open it. If you do not know (clean session, no history): print them all and choose none — guessing ends in the handoff of another thread.",
}


def instruct(*keys):
    print()
    print(" ".join(INSTR[k] for k in keys))


def main():
    data = {}
    for f in candidates():
        ok, h1 = analyze(f)
        if ok:
            data[f] = h1
    everything = sorted(data, key=mtime, reverse=True)
    found, behind = one_per_thread(everything, data)

    def paint(r):
        return line(r, behind.get(key(r, data), 0))

    reason = ""
    foreign = False
    # This used to be `if len(found) > 1`, and with ONE handoff the title was
    # never checked: /lee opened the only one there was even if it belonged to
    # another thread. In a new thread, with no handoff of its own yet, that
    # silently hands over the foreign one -- the same sin as the transcript()
    # fallback removed on 26/08/2026. And with one folder per thread it would
    # be the normal case, not the rare one. Now the title is always checked.
    if found:
        t, reason = title_and_reason()
        of_thread_ = of_thread(t, found, data) if t else []
        if t and not of_thread_:
            foreign = True
            reason = (f"the title is «{t}» and matches none of these; this "
                      "thread probably has no handoff yet")
        if len(of_thread_) == 1:
            print("HANDOFFS: 1")
            print(paint(of_thread_[0]))
            print(f"(chosen by the conversation title, «{t}»; "
                  f"there were {len(everything)} in the directory)")
            instruct("one", "one_title")
            return
        if len(of_thread_) > 1:
            # There can no longer be two of the same thread: one_per_thread()
            # kept only the most recent of each. Getting here means the title
            # matches DIFFERENT threads -- two billing threads sharing two words
            # and saved by a tenth --, and there choosing is the user's call:
            # picking the wrong thread costs more than a question.
            ordered = [r for r in found if r in of_thread_]
            print(f"HANDOFFS: {len(ordered)}")
            for r in ordered:
                print(paint(r))
            print(f"({len(ordered)} different threads match «{t}», newest "
                  f"first; there were {len(everything)} in the directory)")
            instruct("several")
            return

    print(f"HANDOFFS: {len(found)}")
    for head, members in group(found[:MAX], data):
        if head:
            print(f"— {head}")
        for p in members:
            print(paint(p))
    if len(found) > MAX:
        print(f"… and {len(found) - MAX} more, not listed.")
    if reason:
        # Without this line, a list of mixed threads looks like a matcher
        # failure. It is the opposite: it is the matcher refusing to guess.
        retry = (" Run /lee again next turn and only yours will come out."
                 if reason == NO_TITLE else "")
        print(f"(not matched by thread: {reason}.{retry})")
        if len(found) != 1:
            instruct("loose")
        elif foreign:
            instruct("foreign")
        else:
            instruct("only", "one")
        return
    # With no reason and with handoffs we never get here: if the title
    # matched we returned earlier, and if it did not there is a reason. The
    # fallback leans towards not opening: listing too much costs a question,
    # opening too much costs the thread.
    instruct("zero" if not found else "several")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # lee.md says to act "on the number HANDOFFS: gives, and nothing more".
        # Without that line the command is left without an instruction and does
        # anything, which is the worst way to fail. Always a number.
        print("HANDOFFS: 0")
        print(f"(could not list: {type(e).__name__}; this does not mean there "
              "are no handoffs here, it means the search failed)")
        print()
        print(INSTR["failure"])

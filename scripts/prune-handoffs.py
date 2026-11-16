#!/usr/bin/env python3
"""Keeps at most KEEP handoffs of this thread in the working directory.

The extra ones are NOT deleted: they are moved to trash/. Reuses the matcher
in list-handoffs.py so that "same thread" means exactly the same in /pausa
and in /lee.

If the conversation title cannot be read, the thread cannot be identified
and nothing is pruned. Always exits 0.

That brake was illusory until 26/08/2026: `transcript()` had a fallback
that, when the session's own .jsonl was not on disk yet, returned the
PREVIOUS session's. The title was read perfectly -- it just belonged to
another thread --, so the brake never fired and this pruning would have
retired someone else's handoffs. Fixed in pause-name.py: no identifiable
session, no title.
"""
import os, glob, importlib.util, shutil, sys
from datetime import datetime

LIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "list-handoffs.py")
# 2 since 26/08/2026: the current one and its predecessor. The listing only
# shows the most recent of each thread, so the second is not seen -- it is
# announced with "(+1 older in the folder)" and is there in case the last
# one goes wrong. A third no longer earns its place: in 24 sessions there was
# NOT ONE read of a superseded handoff, and what is retired is not deleted,
# it is archived in trash/.
KEEP = 2
DEST = "trash"


def module():
    spec = importlib.util.spec_from_file_location("list_handoffs", LIST)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def free(dest, name):
    base, ext = os.path.splitext(name)
    path, n = os.path.join(dest, name), 2
    while os.path.exists(path):
        path = os.path.join(dest, f"{base}-{n}{ext}")
        n += 1
    return path


def main():
    m = module()
    data = {}
    for f in m.candidates():
        ok, h1 = m.analyze(f)
        if ok:
            data[f] = h1
    keep = KEEP
    if "--before" in sys.argv[1:]:
        # /pausa runs it in its preamble, before writing, and saves a model call
        # with the whole context. Today's is about to be rewritten: it neither
        # counts nor is touched. Of the rest one stays; once the new one is
        # written, KEEP.
        today = f"-{datetime.now():%Y-%m-%d}.md"
        data = {f: h for f, h in data.items() if not f.endswith(today)}
        keep = KEEP - 1
    if len(data) <= keep:
        print("PRUNE: nothing to prune")
        return

    t = m.current_title()
    if not t:
        print("PRUNE: unknown title, nothing pruned")
        return

    thread = m.of_thread(t, sorted(data, key=m.mtime, reverse=True), data)
    if len(thread) <= keep:
        print(f"PRUNE: {len(thread)} of this thread, under the maximum of {keep}")
        return

    # Of the same thread, by date: the oldest are the extra ones.
    bydate = [r for r in sorted(data, key=m.mtime, reverse=True) if r in thread]
    extra = bydate[keep:]
    moved = []
    for r in extra:
        # The trash goes next to the handoff: if the thread lives in its own
        # folder, its retired handoffs stay inside it.
        dest = os.path.join(os.path.dirname(r), DEST)
        os.makedirs(dest, exist_ok=True)
        d = free(dest, os.path.basename(r))
        shutil.move(r, d)
        moved.append(f"{r} → {d} ({m.date(d)})")
    print(f"PRUNE: {len(bydate)} of thread «{t}»; keeping {keep}, retiring {len(moved)}")
    for x in moved:
        print("  " + x)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"PRUNE: no effect ({type(e).__name__})", file=sys.stderr)

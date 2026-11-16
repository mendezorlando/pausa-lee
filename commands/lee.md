---
description: Resumes the thread: opens this directory's handoff, or lists the ones there are for you to choose
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/list-handoffs.py:*), Read
argument-hint: [word-from-the-thread]
---

REQUESTED FILTER: $ARGUMENTS

!`${CLAUDE_PLUGIN_ROOT}/scripts/list-handoffs.py`

Above are the handoffs of this directory and one level of subfolders, newest first, and below them the instruction of the one branch that applies. Follow it to the letter and do nothing else. Always answer in the user's own language.

**If `REQUESTED FILTER` has text, it overrides that instruction.** Keep the lines whose path contains it, ignoring case and accents: if one is left, open it and continue from `Next step`; if several are left, print them whole and exactly as they come, and stop; if none is left, say so in one line and print the whole list exactly as it comes, without opening anything.

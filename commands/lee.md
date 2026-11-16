---
description: Retoma el hilo: abre el handoff de este directorio, o lista los que haya para que elijas
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/lista-handoffs.py:*), Read
argument-hint: [palabra-del-hilo]
---

REQUESTED FILTER: $ARGUMENTS

!`${CLAUDE_PLUGIN_ROOT}/scripts/lista-handoffs.py`

Above are the handoffs of this directory and one level of subfolders, newest first, and below them the instruction of the one branch that applies. Follow it to the letter and do nothing else. Always answer in the user's own language: these instructions are in English, the listing and your reply are not.

**If `REQUESTED FILTER` has text, it overrides that instruction.** Keep the lines whose path contains it, ignoring case and accents: if one is left, open it and continue from `Siguiente paso`; if several are left, print them whole and exactly as they come, and stop; if none is left, say so in one line and print the whole list exactly as it comes, without opening anything.

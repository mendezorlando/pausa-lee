---
description: Writes the handoff to disk before a long pause, so you can /clear without losing the thread
argument-hint: [file-name]
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/pause-name.py:*), Bash(${CLAUDE_PLUGIN_ROOT}/scripts/prune-handoffs.py:*)
---

REQUESTED NAME: $ARGUMENTS
NAME FROM CONVERSATION: !`${CLAUDE_PLUGIN_ROOT}/scripts/pause-name.py`
PRUNE: !`${CLAUDE_PLUGIN_ROOT}/scripts/prune-handoffs.py --before`

I am about to take a long pause. Write the handoff where this thread already lives: `NAME FROM CONVERSATION` carries the whole path, with the thread's own folder if it has one (`OPTIMIZATION/…`) and without it if it lives at the root of the working directory.

**File name.** Resolve it yourself, without asking me, in this order:

1. If `REQUESTED NAME` has text, it wins: normalize it (spaces → `-`, drop `/` and `\`), add today's date as `-YYYY-MM-DD` unless it already has one, end it in `.md` and write it **in the folder that `NAME FROM CONVERSATION` carries**, right away. The requested name is a name, not a path: you do not choose the folder. Check nothing else.
   `UNKNOWN` **is not a folder**: it is the signal that the session could not be identified. If that is what came, write in the working directory and create no folder by that name.
2. If `REQUESTED NAME` is empty, use `NAME FROM CONVERSATION` as is: it is already normalized and carries its folder.
3. Only if `NAME FROM CONVERSATION` is also `UNKNOWN`, pick a short name from the thread's topic, write it in the working directory and tell me which one you chose **and that the thread could not be identified**: without a title there is no matching, so pruning will do nothing and the next `/lee` will not know this handoff belongs to this thread. For it to know, the file's first line matters more than ever.

The name carries the date, so pausing on the same day rewrites that day's file and pausing on another day creates a new one. If today's file already exists, rewrite it whole with the current state. **Do not touch any other `.md` in the directory or its subfolders by hand**, and in particular do not delete earlier days' files: `/lee` lists them with their date for the user to choose which to resume, and trimming them is pruning's job.

**First line of the file.** A `# ` with the conversation's title, exactly, even if the file name is different. `/lee` matches the thread by it when the name does not give it away.

Content, in this order and without filler:

1. **Decided** — decisions that need not be discussed again, one line each.
2. **Touched** — files modified or created, with their relative path and what was done to them.
3. **In progress** — what was left incomplete and the exact point where it stopped.
4. **Next step** — a single imperative sentence. Not a list.
5. **Do not repeat** — paths already ruled out and why, so they are not explored again.

Rules:

- About 2k tokens at most. If it does not fit, cut historical context, never the next step.
- Write numbers and paths, not adjectives. "the XML parser fails on nested CDATA in `src/parse.ts:88`", not "there is a problem with the parser".
- It is a file to be read cold tomorrow, without this conversation. If a sentence only makes sense having been here, rewrite it.

**Pruning.** It is already done: it is the `PRUNE` line above, which ran before you write. It left today's handoff and one earlier one of this thread, and the one you write now completes the two. Do not run it again: your only call is the one that writes the file.

When done, tell me in one line the name of the file written and to run `/clear`, and nothing else.

# pausa-lee

Two Claude Code commands that let you `/clear` without losing the thread (*pausa* and *lee* are Spanish for "pause" and "read"):

- **`/pausa [name]`:** before a long pause, writes a *handoff* to the working directory, `<conversation-title>-YYYY-MM-DD.md`. It has five sections (Decided, Touched, In progress, Next step and Do not repeat) and about 2k tokens at most.
- **`/lee [word]`:** when you come back, finds this thread's handoff by the conversation title, opens it and continues from «Next step». If it cannot tell which thread it is, it lists the handoffs for you to choose and does not guess.

Why it exists: Claude's prompt cache lasts an hour. When you come back, the context you left alive is paid in full on every call. A 2k-token handoff resumes the thread for a fraction of that.

## Install
In a Claude Code session in the terminal:

```
/plugin install pausa-lee --marketplace mendezorlando/pausa-lee
```

From a shell:

```bash
claude plugin install pausa-lee --marketplace mendezorlando/pausa-lee
```

In the desktop app: + next to the prompt box → Plugins → Add marketplace with `mendezorlando/pausa-lee` → Add plugin.

The commands are invoked as `/pausa` and `/lee`. If another command already uses one of those names, as `/pausa-lee:pausa` and `/pausa-lee:lee`.

## How it works
**`scripts/pause-name.py`** derives the file name from the conversation title.
- It identifies the session by `CLAUDE_CODE_SESSION_ID`. If that variable is missing, it walks up the process tree to `~/.claude/sessions/<pid>.json`.
- It reads the title (`custom-title` or `ai-title`) in `~/.claude/projects/*/<session>.jsonl`.
- If a thread already keeps its handoffs in a subfolder, it writes there.
- If it cannot identify the session, it prints `UNKNOWN` and makes nothing up.

**`scripts/list-handoffs.py`** looks for `.md` files in the directory and in one level of subfolders.
- A `.md` counts as a handoff if it has at least 4 of the 5 sections.
- It matches each one to the thread by its name or its H1, and prints only the instruction for the case that applies. That keeps `/lee` cheap in tokens.

**`scripts/prune-handoffs.py`** keeps two handoffs per thread: the current one and the previous one.
- The others are not deleted: they move to `trash/`, next to their file.
- If the title is unknown, it prunes nothing.

**`scripts/test-handoffs.py`** is the regression suite: `python3 scripts/test-handoffs.py`. It works in temporary folders and with a `HOME` of its own.

## Requirements and limits
- Python 3, no dependencies. Works on macOS and Linux, because it uses `ps` to walk up the process tree.
- It reads Claude Code's internal files: the `.jsonl` transcript and `~/.claude/sessions`. If a future version changes that format, matching may stop working. In that case `/lee` lists the handoffs instead of opening one.
- If you rename the conversation, the matcher has a harder time recognizing the thread. The next `/pausa` brings it back in sync.

## License
MIT.

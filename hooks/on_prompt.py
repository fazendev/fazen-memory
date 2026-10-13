# -*- coding: utf-8 -*-
"""UserPromptSubmit hook (Fazen Memory).

1. /fazenmemory [off|status] turns Fazen Memory on or off for this chat (on = code word
   "Si Fratello!", checkpoints, automatic handoff, automatic "yes" to obvious continuations).
2. /fmcodeword sets or clears the phrase (never echoed back to Claude); setting one also turns
   Fazen Memory on.
3. A "Fazen Memory resume" message (first message of a chat opened by a handoff) turns it on and
   re-arms the code word named in the handoff file.
4. A manual /fmhandoff marks the chat so the automatic handoff does not fire again.
5. Counts exchanges; when on, at 20 exchanges or the yellow token mark asks for a checkpoint once.
Never blocks the prompt. Any error exits quietly.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state  # noqa: E402

SWITCH_RE = re.compile(r"^\s*/fazenmemory\b(.*)$", re.IGNORECASE | re.DOTALL)
CODEWORD_RE = re.compile(r"^\s*/fmcodeword\b(.*)$", re.IGNORECASE | re.DOTALL)
HANDOFF_RE = re.compile(r"^\s*/fmhandoff\b", re.IGNORECASE)
RESUME_RE = re.compile(r"Fazen Memory resume:\s*(?:read in full|leggi per intero)\s+`?([^`\n]+?\.md)`?",
                       re.IGNORECASE)
HANDOFF_PHRASE_RE = re.compile(r"Start every reply with exactly \"(.+?)\"")


def _arg(m):
    arg = m.group(1).strip()
    if len(arg) >= 2 and (arg[0] == arg[-1] and arg[0] in "\"'" or (arg[0], arg[-1]) == ("“", "”")):
        arg = arg[1:-1].strip()
    return arg


def parse_codeword(prompt):
    """Return ('on', phrase) | ('off', None) | ('status', None) | None."""
    m = CODEWORD_RE.match(prompt or "")
    if not m:
        return None
    arg = _arg(m)
    if not arg:
        return ("on", state.DEFAULT_PHRASE)
    if arg.lower() in ("off", "status"):
        return (arg.lower(), None)
    return ("on", arg)


def parse_switch(prompt):
    """Return 'on' | 'off' | 'status' | None."""
    m = SWITCH_RE.match(prompt or "")
    if not m:
        return None
    arg = _arg(m).lower()
    return arg if arg in ("off", "status") else "on"


def resumed(prompt):
    """(True, phrase or None) when the prompt is a Fazen Memory resume message, else (False, None)."""
    m = RESUME_RE.search(prompt or "")
    if not m:
        return (False, None)
    try:
        with open(m.group(1).strip(), encoding="utf-8") as f:
            head = f.read(20000)
    except OSError:
        return (True, None)
    found = HANDOFF_PHRASE_RE.search(head)
    return (True, found.group(1) if found else None)


def main():
    data = state.read_stdin_json(sys.stdin)
    session = data.get("session_id", "unknown")
    prompt = data.get("prompt", "")
    st = state.load(session)
    st["auto_continues"] = 0  # the cap counts per user message

    switch = parse_switch(prompt)
    if switch == "on":
        st["enabled"] = True
        st["misses"] = 0
        if not st.get("codeword"):
            st["codeword"] = state.DEFAULT_PHRASE
    elif switch == "off":
        st["enabled"] = False
        st["codeword"] = None

    cmd = parse_codeword(prompt)
    if cmd and cmd[0] == "on":
        st["enabled"] = True
        st["codeword"] = cmd[1]
        st["misses"] = 0
    elif cmd and cmd[0] == "off":
        st["codeword"] = None

    is_resume, carried = resumed(prompt)
    if is_resume:
        st["enabled"] = True
        st["codeword"] = carried
        st["misses"] = 0

    if HANDOFF_RE.match(prompt or ""):
        st["handoff_requested"] = True

    st["turns"] = int(st.get("turns", 0)) + 1
    note = None
    if st.get("enabled"):
        tokens = state.context_tokens(data.get("transcript_path"))
        nudged = st.setdefault("nudged", [])
        if "yellow" not in nudged and (st["turns"] >= state.YELLOW_TURNS or tokens >= state.YELLOW_TOKENS):
            nudged.append("yellow")
            note = (
                "[fazen-memory] This chat is getting long ({0} exchanges, ~{1}k context tokens). "
                "First reply to the user's message exactly as you normally would, following every rule "
                "of this chat. Then, at the end of that same reply, append a checkpoint (fmcheckpoint "
                "skill) with health at least yellow. Do not replace the answer with it."
            ).format(st["turns"], tokens // 1000)
    state.save(session, st)

    if note:
        print(json.dumps({
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": note}
        }))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never break the user's chat
        pass
    sys.exit(0)

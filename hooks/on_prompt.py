# -*- coding: utf-8 -*-
"""UserPromptSubmit hook (Fazen Memory).

1. /fazenmemory [off|status] turns Fazen Memory on or off for this chat (on = code word, by
   default "Yes Brother!" in English or "Si Fratello!" in Italian, checkpoints, automatic
   handoff, automatic "yes" to obvious continuations).
2. /fmcodeword sets or clears the phrase; setting one also turns Fazen Memory on. Claude is told
   the phrase only in the turn that sets it.
3. A "Fazen Memory resume" message (first message of a chat opened by a handoff) turns it on and
   re-arms the code word named in the handoff file.
4. A manual /fmhandoff marks the chat so the automatic handoff does not fire again.
5. Counts exchanges; when on, at 20 exchanges or the yellow token mark asks for a checkpoint once.
6. /fazenmemory status gets the hooks' real data, with a warning when they missed messages.
Never blocks the prompt. Any error exits quietly.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state  # noqa: E402

# As a plugin the commands also run with the plugin prefix: /fazen-memory:fazenmemory.
SWITCH_RE = re.compile(r"^\s*/(?:fazen-memory:)?fazenmemory\b(.*)$", re.IGNORECASE | re.DOTALL)
CODEWORD_RE = re.compile(r"^\s*/(?:fazen-memory:)?fmcodeword\b(.*)$", re.IGNORECASE | re.DOTALL)
HANDOFF_RE = re.compile(r"^\s*/(?:fazen-memory:)?fmhandoff\b", re.IGNORECASE)
RESUME_RE = re.compile(r"Fazen Memory resume:\s*(?:read in full|leggi per intero)\s+`?([^`\n]+?\.md)`?",
                       re.IGNORECASE)
HANDOFF_PHRASE_RE = re.compile(r"Start every reply with exactly \"(.+?)\"")
LANGUAGE_NAMES = {"en": "English", "it": "Italian"}


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
        return ("on", state.default_phrase())
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


def status_note(st, prompt, transcript_path):
    """What the hooks really know, plus a warning when they missed messages (their state was lost)."""
    real, last = state.user_prompts(transcript_path)
    if prompt.strip() not in last:
        real += 1  # the current prompt is not in the transcript yet
    note = ("[fazen-memory] Hooks status for /fazenmemory status: Fazen Memory {0}; code word: {1}; "
            "messages counted by the hooks: {2} of {3}; handoff already requested: {4}; state folder: {5}."
            ).format("on" if st.get("enabled") else "off", st.get("codeword") or "none", st["turns"], real,
                     "yes" if st.get("handoff_requested") else "no", state.state_dir())
    if real - st["turns"] >= 2:
        note += (" Warning: the hooks missed {0} of {1} messages. Either Fazen Memory was installed in the "
                 "middle of this chat, or something deletes the state folder (for example a cleanup script "
                 "or hook). While that happens, checkpoints and the automatic handoff cannot work. Show this "
                 "warning to the user.").format(real - st["turns"], real)
    return note


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
            st["codeword"] = state.default_phrase()
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
    notes = []
    if switch == "on" or (cmd and cmd[0] == "on"):
        # Only in the turn that sets it: the code word stays a memory test in later turns.
        notes.append((
            "[fazen-memory] Fazen Memory is on in this chat. Code word: start this reply and every "
            "later one with exactly \"{0}\". Plugin language: {1}; write Fazen Memory's messages "
            "to the user in it unless they write in another language."
        ).format(st["codeword"], LANGUAGE_NAMES[state.language()]))
    if switch == "status":
        notes.append(status_note(st, prompt, data.get("transcript_path")))
    if st.get("enabled"):
        tokens = state.context_tokens(data.get("transcript_path"))
        nudged = st.setdefault("nudged", [])
        if "yellow" not in nudged and (st["turns"] >= state.YELLOW_TURNS or tokens >= state.YELLOW_TOKENS):
            nudged.append("yellow")
            notes.append((
                "[fazen-memory] This chat is getting long ({0} exchanges, ~{1}k context tokens). "
                "First reply to the user's message exactly as you normally would, following every rule "
                "of this chat. Then, at the end of that same reply, append a checkpoint (fmcheckpoint "
                "skill) with health at least yellow. Do not replace the answer with it."
            ).format(st["turns"], tokens // 1000))
    state.save(session, st)

    if notes:
        print(json.dumps({
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "\n".join(notes)}
        }))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never break the user's chat
        pass
    sys.exit(0)

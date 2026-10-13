# -*- coding: utf-8 -*-
"""Stop hook (Fazen Memory). Does nothing in chats where Fazen Memory is off.

- Code word missing at the start of both the turn's first text and the final reply -> warn the user
  (systemMessage).
- Red signal (code word missed, 35 exchanges, or the red token mark) -> once per chat, block the
  stop and tell Claude to run the fmhandoff skill in AUTO mode now: handoff file, new chat in the
  same folder in auto mode, link back to the user.
- The reply ends with one obvious continuation question ("Shall I continue with step 2?") ->
  answer yes for the user (at most MAX_AUTO_CONTINUE times per user message). Never for choices,
  several questions, or anything that is the user's decision (merge, production, money, legal,
  sending, deleting).
The phrase itself is never sent to Claude, so the code word stays a real memory test.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state  # noqa: E402

LEADING_NOISE = re.compile(r"^[\s*_#>`~\-]+")
CODE_BLOCK = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)
CONTINUE_WORDS = re.compile(
    r"continu|prosegu|proced|avanti|\bpass(o|iamo|are) (a|al|allo|alla|ai|agli|alle)\b|\bpart(o|iamo|ire)\b"
    r"|prossim[oa] (passo|punto|step|fase)|go ahead|move on|next step|proceed|carry on|keep going")
CHOICE_WORDS = re.compile(r"\b(o|oppure|or|vs|versus)\b")
# The user's decisions: never answered automatically (folded: lowercase, no accents).
GATED_WORDS = re.compile(
    r"merge|deploy|produzion|\bprod\b|production|\bpush|pubblic|publish|rilasc|release|pagam|pagare|acquist"
    r"|\bcompr[aoi]\b|comprare|\bspes[ae]\b|\bcost[oi]\b|fattur|bonific|elimin|cancell|delet|\bdrop\b|rimuov"
    r"|\breset|force|\binvi[aoi]\b|inviare|\bsend|e-?mail|messaggi|whatsapp|slack|legal|contratt|archivi"
    r"|migrazion|migration|password|segret|secret|api key"
    r"|\bpay|purchas|\bbuy|invoic|remov|contract|messag")


def _is_real_prompt(entry):
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isCompactSummary"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        types = {c.get("type") for c in content if isinstance(c, dict)}
        return "tool_result" not in types and bool(types & {"text", "image", "document"})
    return False


def turn_texts(transcript_path):
    """Assistant texts written after the latest real user prompt, in order.
    Empty when that prompt is not inside the transcript tail (then the caller falls back)."""
    entries = state.tail_entries(transcript_path)
    last_prompt = -1
    for i, e in enumerate(entries):
        if _is_real_prompt(e):
            last_prompt = i
    if last_prompt < 0:
        return []
    texts = []
    for e in entries[last_prompt + 1:]:
        if e.get("type") != "assistant" or e.get("isSidechain"):
            continue
        content = (e.get("message") or {}).get("content")
        if isinstance(content, str) and content.strip():
            texts.append(content)
        elif isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text" and c.get("text", "").strip():
                    texts.append(c["text"])
    return texts


def reply_start(transcript_path, last_message):
    """First text of this turn. The transcript can lag behind the Stop event, so trust it only
    once its last text matches last_assistant_message."""
    for _ in range(10):
        texts = turn_texts(transcript_path) if transcript_path else []
        if texts and (not last_message or texts[-1].strip()[:200] == last_message.strip()[:200]):
            return texts[0]
        if not last_message and not transcript_path:
            return None
        time.sleep(0.2)
    return last_message or None


def opens_with(text, phrase):
    return state.fold(LEADING_NOISE.sub("", text or "")).startswith(state.fold(phrase))


def obvious_continuation(message):
    """The closing question when the reply ends with exactly one yes/no 'shall I continue?'
    question that is not the user's decision; otherwise None."""
    prose = CODE_BLOCK.sub(" ", message or "").rstrip().rstrip("*_)\"'» ")
    if not prose.endswith("?") or prose.count("?") != 1:
        return None
    start = max(prose.rfind(c, 0, len(prose) - 1) for c in ".!:\n")
    question = prose[start + 1:].strip()
    folded_q = state.fold(question)
    if not CONTINUE_WORDS.search(folded_q) or CHOICE_WORDS.search(folded_q):
        return None
    if GATED_WORDS.search(state.fold(prose[-600:])):
        return None
    return question


def main():
    data = state.read_stdin_json(sys.stdin)
    session = data.get("session_id", "unknown")
    st = state.load(session)
    if not st.get("enabled"):
        return
    last_message = data.get("last_assistant_message") or ""

    def auto_continue():
        if not state.attended() or int(st.get("auto_continues", 0)) >= state.MAX_AUTO_CONTINUE:
            return None
        question = obvious_continuation(last_message)
        if not question:
            return None
        st["auto_continues"] = int(st.get("auto_continues", 0)) + 1
        return {
            "decision": "block",
            "reason": (
                "[fazen-memory] Auto-continue: the user pre-approved obvious continuation questions. "
                "Your question \"{0}\" is answered YES: carry on now with exactly what you proposed. "
                "Do not ask again before the next obvious step; stop only for the user's real "
                "decisions (merge, production, money, legal, sending anything external, deleting) or "
                "a genuinely open choice."
            ).format(question[:300]),
            "systemMessage": state.message("auto_yes", question[:120], st["auto_continues"],
                                           state.MAX_AUTO_CONTINUE),
        }

    if data.get("stop_hook_active"):  # continuing after a block: only the capped auto-continue chains
        out = auto_continue()
        if out:
            state.save(session, st)
            print(json.dumps(out))
        return

    reasons = []
    warnings = []

    turns = int(st.get("turns", 0))
    tokens = state.context_tokens(data.get("transcript_path"))
    phrase = st.get("codeword")
    if phrase:
        text = reply_start(data.get("transcript_path"), last_message)
        # One user prompt can drive a long autonomous turn whose first text is a progress note:
        # the code word at the start of the final reply counts too.
        if text and text.strip() and not opens_with(text, phrase) and not opens_with(last_message, phrase):
            st["misses"] = int(st.get("misses", 0)) + 1
            warnings.append(state.message("miss"))
            if turns >= state.MISS_MIN_TURNS or tokens >= state.MISS_MIN_TOKENS:
                reasons.append("the code word was missing from the last reply")

    if turns >= state.RED_TURNS:
        reasons.append("the chat reached {0} exchanges".format(turns))
    if tokens >= state.RED_TOKENS:
        reasons.append("the context reached ~{0}k tokens".format(tokens // 1000))

    out = {}
    if reasons and state.AUTO_HANDOFF and state.attended() and not st.get("handoff_requested"):
        st["handoff_requested"] = True
        out["decision"] = "block"
        out["reason"] = (
            "[fazen-memory] Red signal: {0}. Run the fmhandoff skill in AUTO mode now: write the "
            "handoff file, start the new chat in this same folder in auto permission mode, switch "
            "to it, and tell the user, in their language, that the work moved to the new chat, with its link. If you were "
            "waiting on the user for a decision, record it in section 12 and still hand off."
        ).format("; ".join(reasons))
        warnings.append(state.message("handoff"))
    else:
        if reasons and not st.get("red_warned"):
            st["red_warned"] = True
            warnings.append(state.message("red"))
        cont = auto_continue()
        if cont:
            out["decision"], out["reason"] = cont["decision"], cont["reason"]
            warnings.append(cont["systemMessage"])
    state.save(session, st)

    if warnings:
        out["systemMessage"] = " ".join(warnings)
    if out:
        print(json.dumps(out))  # ASCII escapes: Windows stdout is cp1252 and chokes on emoji


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never break the user's chat
        pass
    sys.exit(0)

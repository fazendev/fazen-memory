# -*- coding: utf-8 -*-
"""Fazen Memory: per-session state shared by the hooks (fork of active-memory 0.2.6, MIT).

State lives in $CLAUDE_PLUGIN_DATA/sessions/<session_id>.json (plugin) or ~/.claude/fazen-memory/sessions/ and is never shown to Claude.
"""
import json
import locale
import os
import re
import unicodedata

# Fazen Memory is off in a chat until the user types /fazenmemory (or the chat was opened by a
# Fazen Memory handoff). Off = the hooks only count exchanges, nothing else.
DEFAULT_PHRASES = {"en": "Yes Brother!", "it": "Si Fratello!"}
MESSAGES = {
    "en": {
        "auto_yes": u"▶️ Fazen Memory: answered yes automatically to “{0}” ({1}/{2})",
        "miss": "🐤 Fazen Memory: the reply did not start with the code word.",
        "handoff": "🧠 Fazen Memory: red signal, starting the automatic handoff to a new chat.",
        "red": "🔴 Fazen Memory: this chat is long, run /fmhandoff to move to a new chat.",
    },
    "it": {
        "auto_yes": u"▶️ Fazen Memory: ho risposto sì in automatico a “{0}” ({1}/{2})",
        "miss": "🐤 Fazen Memory: la risposta non è iniziata con la code word.",
        "handoff": "🧠 Fazen Memory: segnale rosso, parte l'handoff automatico in una nuova chat.",
        "red": "🔴 Fazen Memory: questa chat è lunga, usa /fmhandoff per passare a una nuova chat.",
    },
}
MAX_AUTO_CONTINUE = 5  # automatic "yes, continue" answers per user message
# A missed code word means drift only in a chat that is already long; in a fresh chat (e.g. the
# first reply after a handoff) it is a slip, and a handoff there would loop.
MISS_MIN_TURNS = 10
MISS_MIN_TOKENS = 200000
YELLOW_TURNS = 20
RED_TURNS = 35
# Tokens of conversation (see conversation_tokens): the fixed overhead (system prompt, tools,
# skills, MCP; ~116k seen live) is not conversation and does not count. Red stays well under
# Claude Code's own auto-compact (97% of a 1M window), leaving room to write the handoff.
YELLOW_TOKENS = int(os.environ.get("FAZEN_MEMORY_YELLOW_TOKENS", "450000"))
RED_TOKENS = int(os.environ.get("FAZEN_MEMORY_RED_TOKENS", "700000"))
# FAZEN_MEMORY_AUTO=0 keeps the warnings but never forces the automatic handoff.
AUTO_HANDOFF = os.environ.get("FAZEN_MEMORY_AUTO", "1") != "0"


def fold(text):
    """Lowercase without accents, so "Sì Fratello!" still matches "Si Fratello!"."""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).lower()


def _lang_code(name):
    """'it' for any Italian name ("italian", "Italiano", "it_IT", "Italian_Italy"), else 'en'."""
    return "it" if fold(name or "").startswith("it") else "en"


def language():
    """Language of the messages shown to the user and of the default code word.

    The plugin's `language` option (exported to hooks as CLAUDE_PLUGIN_OPTION_LANGUAGE) wins;
    with "auto" or no option: Claude Code's own `language` setting, then the system language."""
    option = os.environ.get("CLAUDE_PLUGIN_OPTION_LANGUAGE", "auto").strip()
    if option and fold(option) != "auto":
        return _lang_code(option)
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    try:
        with open(os.path.join(config_dir, "settings.json"), encoding="utf-8") as f:
            setting = json.load(f).get("language")
        if isinstance(setting, str) and setting.strip():
            return _lang_code(setting)
    except (OSError, ValueError, AttributeError):
        pass
    # Not $LANG: Git Bash sets it to en_US even on an Italian Windows. Python already applies
    # LANG/LC_* to this locale on Linux and macOS.
    return _lang_code(locale.getlocale()[0])


def default_phrase():
    """The plugin's `codeword` option, else "Si Fratello!" / "Yes Brother!" by language."""
    return os.environ.get("CLAUDE_PLUGIN_OPTION_CODEWORD", "").strip() or DEFAULT_PHRASES[language()]


def message(key, *args):
    return MESSAGES[language()][key].format(*args)


def attended():
    """A person is in the chat: desktop app / interactive CLI. False for `claude -p`, SDK scripts,
    scheduled and other unattended runs, where a forced handoff or an automatic "yes" has nobody
    to continue with."""
    flag = os.environ.get("CLAUDE_CODE_SESSION_ATTENDED")
    if flag is not None:
        return flag == "1"
    return os.environ.get("CLAUDE_CODE_ENTRYPOINT") == "cli"


def state_dir():
    # Installed as a plugin: Claude Code's per-plugin data folder (kept across updates).
    root = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(os.path.expanduser("~"), ".claude", "fazen-memory")
    base = os.path.join(root, "sessions")
    os.makedirs(base, exist_ok=True)
    return base


def _path(session_id):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "unknown")
    return os.path.join(state_dir(), safe + ".json")


def load(session_id):
    try:
        with open(_path(session_id), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"enabled": False, "turns": 0, "codeword": None, "misses": 0, "nudged": [],
                "handoff_requested": False, "auto_continues": 0}


def save(session_id, data):
    path = _path(session_id)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def read_stdin_json(stream):
    try:
        raw = stream.buffer.read().decode("utf-8") if hasattr(stream, "buffer") else stream.read()
        return json.loads(raw or "{}")
    except (ValueError, OSError, UnicodeDecodeError):
        return {}


TAIL_BYTES = 8 * 1024 * 1024


def tail_entries(transcript_path):
    """Parsed JSONL entries from the last TAIL_BYTES of the transcript.

    Transcripts reach hundreds of MB; parsing them whole takes seconds per read and
    pushes the hooks past their timeout. Everything the hooks need is near the end.
    """
    if not transcript_path:
        return []
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - TAIL_BYTES))
            data = f.read()
    except OSError:
        return []
    lines = data.split(b"\n")
    if size > TAIL_BYTES:
        lines = lines[1:]  # first line is cut in the middle
    entries = []
    for line in lines:
        if line.strip():
            try:
                entries.append(json.loads(line.decode("utf-8")))
            except (ValueError, UnicodeDecodeError):
                continue
    return entries


def user_prompts(transcript_path):
    """(number of messages the user typed in this chat, text of the last one).

    Reads the whole transcript, so only /fazenmemory status calls it. Tool results, skill
    bodies and hook feedback are logged as user entries too; they are not prompts.
    """
    count, last = 0, ""
    try:
        with open(transcript_path, "rb") as f:
            for line in f:
                # Cheap byte filters first: parsing every line of a big transcript is too slow.
                if b'"user"' not in line or b'"tool_result"' in line:
                    continue
                try:
                    e = json.loads(line.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    continue
                if e.get("type") != "user" or e.get("isMeta") or e.get("isSidechain") or e.get("isCompactSummary"):
                    continue
                content = (e.get("message") or {}).get("content")
                if isinstance(content, list):
                    content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
                count, last = count + 1, content or ""
    except (OSError, TypeError):
        return (0, "")
    return (count, last)


def _call_tokens(entry):
    """Context size of one main-chat assistant call (input + cache creation + cache read), else None."""
    if entry.get("type") != "assistant" or entry.get("isSidechain"):
        return None
    usage = (entry.get("message") or {}).get("usage")
    if not usage:
        return None
    return int(usage.get("input_tokens", 0)) + int(usage.get("cache_creation_input_tokens", 0)) + int(
        usage.get("cache_read_input_tokens", 0))


def context_tokens(transcript_path):
    """Context size of the latest assistant call."""
    for entry in reversed(tail_entries(transcript_path)):
        n = _call_tokens(entry)
        if n is not None:
            return n
    return 0


def base_tokens(transcript_path):
    """Context size of the chat's first assistant call: the fixed overhead plus the first prompt."""
    try:
        with open(transcript_path, "rb") as f:
            for line in f:
                if b'"usage"' not in line:  # cheap filter: most lines carry no usage
                    continue
                try:
                    n = _call_tokens(json.loads(line.decode("utf-8")))
                except (ValueError, UnicodeDecodeError):
                    continue
                if n is not None:
                    return n
    except (OSError, TypeError):
        pass
    return 0


def conversation_tokens(transcript_path):
    """Tokens the conversation itself adds to the context, without the fixed overhead."""
    return max(0, context_tokens(transcript_path) - base_tokens(transcript_path))

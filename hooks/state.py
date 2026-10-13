# -*- coding: utf-8 -*-
"""Fazen Memory: per-session state shared by the hooks (fork of active-memory 0.2.6, MIT).

State lives in $CLAUDE_PLUGIN_DATA/sessions/<session_id>.json (plugin) or ~/.claude/fazen-memory/sessions/ and is never shown to Claude.
"""
import json
import os
import re
import unicodedata

# Fazen Memory is off in a chat until the user types /fazenmemory (or the chat was opened by a
# Fazen Memory handoff). Off = the hooks only count exchanges, nothing else.
DEFAULT_PHRASE = "Si Fratello!"
MAX_AUTO_CONTINUE = 5  # automatic "yes, continue" answers per user message
# A missed code word means drift only in a chat that is already long; in a fresh chat (e.g. the
# first reply after a handoff) it is a slip, and a handoff there would loop.
MISS_MIN_TURNS = 10
MISS_MIN_TOKENS = 200000
YELLOW_TURNS = 20
RED_TURNS = 35
# Context size (tokens) read from the transcript. The window is 1M but ~110k is fixed
# overhead (tools, skills, MCP), and quality drops long before the window fills.
YELLOW_TOKENS = int(os.environ.get("FAZEN_MEMORY_YELLOW_TOKENS", "300000"))
RED_TOKENS = int(os.environ.get("FAZEN_MEMORY_RED_TOKENS", "450000"))
# FAZEN_MEMORY_AUTO=0 keeps the warnings but never forces the automatic handoff.
AUTO_HANDOFF = os.environ.get("FAZEN_MEMORY_AUTO", "1") != "0"


def fold(text):
    """Lowercase without accents, so "Sì Fratello!" still matches "Si Fratello!"."""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).lower()


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


def context_tokens(transcript_path):
    """Context size of the latest assistant call: input + cache creation + cache read."""
    for entry in reversed(tail_entries(transcript_path)):
        if entry.get("type") != "assistant" or entry.get("isSidechain"):
            continue
        if not (entry.get("message") or {}).get("usage"):
            continue
        usage = (entry.get("message") or {}).get("usage") or {}
        return int(usage.get("input_tokens", 0)) + int(usage.get("cache_creation_input_tokens", 0)) + int(
            usage.get("cache_read_input_tokens", 0))
    return 0

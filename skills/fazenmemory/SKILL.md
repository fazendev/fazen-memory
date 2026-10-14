---
name: fazenmemory
description: "Fazen Memory on/off switch for this chat. Use when the user types \"/fazenmemory\", \"/fazenmemory off\" or \"/fazenmemory status\", or asks to turn Fazen Memory on or off. On = a code word at the start of every reply (default \"Yes Brother!\" in English, \"Si Fratello!\" in Italian), checkpoints, automatic handoff to a new chat in auto mode when the chat gets too long, and automatic yes to obvious continuation questions."
metadata:
  version: "1.2.0"
---

# Fazen Memory: switch

Fazen Memory is **off** in a new chat until the user types `/fazenmemory`. A chat opened by a Fazen Memory handoff starts **on** by itself. The plugin's hooks do the counting and checking; this skill tells Claude how to behave.

## Argument

- **Empty** → turn on.
- **`off`** → turn off: code word, checkpoints, automatic handoff and auto-continue all stop.
- **`status`** → one line per item, from this turn's `[fazen-memory]` status note: on/off, code word, messages counted by the hooks, whether a handoff was already requested. If the note has a warning, show it word for word as the last line. No note: say that the plugin's hooks are not running in this chat.

## Turn on

1. Start this reply with exactly the phrase named in this turn's `[fazen-memory]` note. No note (the hooks are not running): `Yes Brother!` if the user writes in English, `Si Fratello!` if in Italian, and say in one line that automatic checking is off until the plugin's hooks run. Follow it with a space.
2. Confirm in at most 5 short lines, in the plugin language the note names (otherwise the user's language):
   - Code word **<phrase>** active: a reply without it means the chat may be drifting; in a long chat the second miss moves it to a new chat on its own.
   - 🟡 checkpoint at 20 exchanges / ~450k tokens of conversation; 🔴 automatic handoff at 35 exchanges / ~700k tokens / code word missing twice.
   - Auto-continue on: no more "shall I continue?" on obvious next steps.
   - `/fazenmemory off` turns everything off.
3. From now on, for the rest of this chat, follow the rules below.

## Rules while on

**Code word.** Start **every** reply with the exact phrase, including short replies, code-only replies, error messages and replies after tool use. Never paraphrase, translate or restyle it (the hooks tolerate "Sì" for "Si", nothing else).

**Auto-continue (the user's explicit request).** The user pre-approved obvious next steps. Do not end a reply with questions like "Shall I continue with step 2?", "Proceed?" (Italian: "Posso continuare con il punto 2?", "Procedo?"): when the next step is the obvious continuation of an agreed plan or of what the user asked, do it in the same turn. Verify as you go, as always.

Still stop and ask, clearly and once, only for:
- the user's decisions: merge, production deploy, spending money, legal, sending anything external (email, messages, posts), deleting data or files, archiving sessions;
- a genuinely open choice between options (then lay out the options with a recommendation);
- missing data that cannot be found in the chat, the code or the docs.

As a safety net, if a reply does end with one obvious continuation question, the Stop hook answers yes automatically (at most 5 times per user message, never for the decisions above, never for "A or B?" choices or replies with several questions). When that happens, just continue with what you proposed.

**Checkpoints and handoff.** When a `[fazen-memory]` note asks for a checkpoint, run `fmcheckpoint` after answering. When it reports a red signal, run `fmhandoff` in AUTO mode.

## Turn off

Reply without the code word. Confirm in one line that Fazen Memory is off and `/fazenmemory` turns it back on.

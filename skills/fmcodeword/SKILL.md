---
name: fmcodeword
description: "Fazen Memory code word. Use when the user types \"/fmcodeword\", \"/fmcodeword off\", \"/fmcodeword status\", \"/fmcodeword <phrase>\", or asks to set, change or turn off a code word (\"inizia ogni risposta con…\"). Claude opens every reply with a fixed phrase (default \"Yes Brother!\" in English, \"Si Fratello!\" in Italian); the first reply without it shows the chat is drifting, and the Fazen Memory hooks then start the automatic handoff to a new chat."
metadata:
  version: "1.1.0"
  forked-from: "active-memory 0.2.6 (MIT, Klopyy)"
---

# Fazen Memory: code word

The code word is an early-warning sign for long chats. Claude opens every reply with a fixed phrase. Following an instruction given many messages ago is exactly what weakens as a chat grows, so the first reply that forgets the phrase shows the chat is drifting. The hooks check every reply; on a miss they start the automatic handoff (`fmhandoff`, AUTO mode) once per chat.

`/fazenmemory` turns on Fazen Memory with the default phrase: the plugin's `codeword` setting, otherwise **Yes Brother!** in English or **Si Fratello!** in Italian (the plugin's `language` setting). This command changes the phrase, turns only the code word off, or checks it. Setting a phrase with it also turns Fazen Memory on.

## Read the argument

Text after the command:

- **Empty** → turn on with the default phrase
- **`off`** (any case) → turn the code word off (the rest of Fazen Memory stays on)
- **`status`** → report whether a code word is active in this chat and what it is
- **Anything else** → turn on with that exact text. Strip one pair of surrounding quotes. Keep capitalization and punctuation exactly.

If the user asked in plain words instead of the command, extract the phrase the same way. The hooks only learn the phrase from `/fmcodeword` or `/fazenmemory`; if it was set in plain words, say in one line that automatic checking needs `/fmcodeword <phrase>`.

## Turn on

1. Start this very reply with the phrase, exactly as written, followed by a space. For the default phrase use the phrase named in this turn's `[fazen-memory]` note. No note (the hooks are not running): `Yes Brother!` if the user writes in English, `Si Fratello!` if in Italian.
2. Confirm in 2-4 short lines, in the user's language: the active phrase; that a reply without it means the chat is drifting and Fazen Memory will hand off to a new chat automatically; `/fmcodeword off` turns it off.
3. From now until it is turned off, begin **every** reply with the exact phrase, including very short replies, code-only replies, error messages, and replies after tool use. Never paraphrase, translate, or restyle it (the hooks ignore accents, so "Sì" for "Si" is fine).

If the phrase is one Claude already tends to start with ("Okay", "Sure", "Perfetto", a bare "Fratello"), say in one line that a miss would be harder to spot and suggest the default phrase. Use the user's choice if they keep it.

## Turn off

Reply without the phrase. Confirm in one line that it is off and that `/fmcodeword` turns it back on.

## When the user reports a missing code word

Check the previous reply. If it did start with the phrase, say so in one line and continue.

If it really was missing: start the reply with the phrase, say in one line that the miss means the chat is long enough to lose track, then run the `fmhandoff` skill in AUTO mode.

## Rules

- Never claim the code word proves Claude remembers everything. It is a warning sign, not a guarantee.
- It applies only to this chat. A chat opened by `fmhandoff` gets the same phrase back on its own (section 0 of the handoff file + the resume message); any other new chat starts off until `/fazenmemory`.
- The hooks name the phrase to Claude only in the turn that sets it, never later, so remembering it stays a real test.

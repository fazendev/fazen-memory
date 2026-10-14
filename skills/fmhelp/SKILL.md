---
name: fmhelp
description: "Fazen Memory guide. Use when the user types \"/fmhelp\" or asks how Fazen Memory, the code word, checkpoints, auto-continue or the automatic handoff to a new chat work."
metadata:
  version: "1.2.0"
---

# Fazen Memory: help

Show the guide in the user's language: the Italian version if they write in Italian, the English version otherwise (translated faithfully for any other language). In the code word rows write the phrase active in this chat, or the default for that language if none is active. If a code word is active, the reply still starts with it.

**English**

```
🧠 **Fazen Memory: long chats move to a fresh chat on their own**

| Command | What it does |
|---|---|
| `/fazenmemory` | **Turns on** Fazen Memory in this chat (`/fazenmemory off` turns it off, `/fazenmemory status` checks it) |
| `/fmcodeword [phrase\|off]` | Changes the code word (default **Yes Brother!**) or turns it off |
| `/fmcheckpoint` | Compact recap + health 🟢🟡🔴 (red → automatic handoff) |
| `/fmhandoff` | Full handoff + a new chat in the same folder in auto mode, with its link (`/fmhandoff file` = the file only) |
| `/fmhelp` | This guide |

**While it is on**
- Every reply starts with **Yes Brother!**: when it is missing, the chat may be losing track (in a long chat: a reminder the first time, a handoff the second)
- Tokens count the conversation only, not the fixed part of the chat (tools, skills, MCP)
- 🟡 20 exchanges or ~450k tokens → checkpoint at the end of the reply
- 🔴 35 exchanges, ~700k tokens or the code word missing twice → automatic handoff to a new chat in auto mode, with its link (once per chat)
- ▶️ Auto-continue: no more "shall I continue with step 2?"; if one slips out, it is answered yes automatically (max 5 per message). Never for merge, production, money, legal, sending, deleting or A/B choices

Chats opened by a handoff start already on. Without a person in the chat (`claude -p`, scheduled tasks): warnings only.

**Plugin settings:** Language (auto / english / italian) and Default code word, asked when you enable the plugin and changeable in `/config`.
**Environment variables:** `FAZEN_MEMORY_YELLOW_TOKENS`, `FAZEN_MEMORY_RED_TOKENS`, `FAZEN_MEMORY_AUTO=0` (warnings only, no forced handoff).
```

Then one line for this chat: Fazen Memory off → "💡 Off in this chat: `/fazenmemory` turns it on."; a code word miss or a long chat → "🔴 Shall I move to a new chat now?"; otherwise "✅ All good."

**Italiano**

```
🧠 **Fazen Memory: le chat lunghe passano da sole a una chat nuova**

| Comando | Cosa fa |
|---|---|
| `/fazenmemory` | **Accende** Fazen Memory in questa chat (`/fazenmemory off` spegne, `/fazenmemory status` controlla) |
| `/fmcodeword [frase\|off]` | Cambia la code word (default **Si Fratello!**) o la spegne |
| `/fmcheckpoint` | Riepilogo compatto + salute 🟢🟡🔴 (rosso → handoff automatico) |
| `/fmhandoff` | Handoff completo + nuova chat nella stessa cartella in modalità auto, con link (`/fmhandoff file` = solo il file) |
| `/fmhelp` | Questa guida |

**Quando è accesa**
- Ogni risposta inizia con **Si Fratello!**: se manca, la chat può perdere il filo (in una chat lunga: un promemoria la prima volta, l'handoff la seconda)
- I token contano solo la conversazione, non la parte fissa della chat (tool, skill, MCP)
- 🟡 20 scambi o ~450k token → checkpoint in coda alla risposta
- 🔴 35 scambi, ~700k token o code word mancante due volte → handoff automatico in una nuova chat in auto, con link (una volta per chat)
- ▶️ Auto-continua: niente "posso continuare col punto 2?"; se scappa, il sì arriva in automatico (max 5 per messaggio). Mai su merge, produzione, soldi, legale, invii, cancellazioni o scelte A/B

Le chat nate da un handoff partono già accese. Senza persona (`claude -p`, task programmati): solo avvisi.

**Impostazioni del plugin:** Language (auto / english / italian) e Default code word, chieste quando attivi il plugin e modificabili da `/config`.
**Variabili d'ambiente:** `FAZEN_MEMORY_YELLOW_TOKENS`, `FAZEN_MEMORY_RED_TOKENS`, `FAZEN_MEMORY_AUTO=0` (solo avvisi, niente handoff forzato).
```

Poi una riga per questa chat: Fazen Memory spenta → "💡 Spenta in questa chat: `/fazenmemory` per accenderla."; code word mancata o chat lunga → "🔴 Passo a una chat nuova adesso?"; altrimenti "✅ Tutto a posto."

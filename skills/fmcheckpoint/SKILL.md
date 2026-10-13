---
name: fmcheckpoint
description: "Fazen Memory checkpoint. Use when the user types \"/fmcheckpoint\", or says \"recap\", \"riepilogo\", \"a che punto siamo\", \"stai perdendo il filo\", \"te l'avevo già detto\", \"avevamo già deciso\", or when a [fazen-memory] hook note asks for a checkpoint. Also use it unasked at about 20 exchanges, when large files or pastes pile up, or when Claude contradicts or forgets something already settled. Writes a compact recap plus a green, yellow or red health check; red leads to the automatic handoff."
metadata:
  version: "1.0.0"
  forked-from: "active-memory 0.2.6 (MIT, Klopyy)"
---

# Fazen Memory: checkpoint

Long chats get less reliable because early details get less attention. Rewriting the essentials in a short recap puts them back in focus; the health check says honestly whether a fresh chat is due.

## When to run

**On request:** always.

**Unasked,** at a natural break (never in the middle of a multi-step tool run):

| Signal | Health |
|---|---|
| About 20 exchanges, or a hook note says the yellow mark was reached | 🟡 Yellow at least |
| About 35 exchanges | 🔴 Red |
| The user corrects something already decided, or Claude re-asks a settled question, forgets a name, file, rule, or language/format preference | 🔴 Red |
| The user reports a missing code word | 🔴 Red |
| Many large pastes, files, images, or long outputs | Raise one level |
| Context usage visible (`get_usage`): over ~30% / over ~45% of the window | 🟡 / 🔴 |

When running unasked, **first answer the user's current message in full**, then add the checkpoint below it. Do not run unasked more than once per stage.

## Steps

1. Re-read the whole conversation from the first message, with extra weight on early messages and every correction.
2. Keep only what is needed to keep working. Copy names, numbers, files, versions and rules exactly. Never round or guess. Write "nessuno" for an empty section.
3. When two parts disagree, the latest user statement wins; the older one goes to **Cambiato / scartato**.
4. Pick the health level honestly from the table.
5. Write the checkpoint in the user's language, every section included. Put every user correction under **Regole da ricordare**. If a code word is active, the reply still starts with it.
6. From here on the recap is the source of truth; if the user corrects it, fix it and follow the correction.
7. **Red:** after the checkpoint, run the `fmhandoff` skill in AUTO mode in the same turn (unless the user said not to). Do not just suggest it.

## Format

```
📌 **Checkpoint: <🟢 Verde | 🟡 Giallo | 🔴 Rosso>**

**Obiettivo:** <1-2 lines>

**Decisioni prese:**
- <final choices only>

**Cambiato / scartato:**
- <old → new, or rejected idea>

**Dettagli chiave:** <exact names, files, numbers, versions, formats>

**Fatto finora:** <short bullets>

**Aperto / prossimi passi:**
1. <in order>

**Regole da ricordare:** <stated preferences, constraints, corrections>

<⚠️ or ✅> **Salute:** <one sentence>
```

Then the line that applies:

- **Yellow:** "💡 La chat si allunga: al prossimo punto buono passo a una chat nuova (`/fmhandoff`)."
- **Red:** "🔴 Passo ora a una chat nuova." (then hand off, step 7)
- **Fazen Memory off in this chat:** "💡 Fazen Memory spenta: `/fazenmemory` e inizio ogni risposta con 'Si Fratello!', con checkpoint, handoff automatico e auto-continua."

Keep it under about 300 words. It is a refresher, not the handoff file.

## Rules

- Never invent details. Never include secrets: write "[secret removed]".
- A checkpoint does not reset memory; never claim it does. Green means "fine for now".

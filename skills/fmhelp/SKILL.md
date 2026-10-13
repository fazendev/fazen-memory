---
name: fmhelp
description: "Fazen Memory guide. Use when the user types \"/fmhelp\" or asks how Fazen Memory, the code word, checkpoints, auto-continue or the automatic handoff to a new chat work."
metadata:
  version: "1.1.0"
---

# Fazen Memory: help

Show this guide in Italian. If a code word is active, the reply still starts with it.

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
- Ogni risposta inizia con **Si Fratello!**: se manca, la chat sta perdendo il filo
- 🟡 20 scambi o ~300k token → checkpoint in coda alla risposta
- 🔴 35 scambi, ~450k token o code word mancante → handoff automatico in una nuova chat in auto, con link (una volta per chat)
- ▶️ Auto-continua: niente "posso continuare col punto 2?"; se scappa, il sì arriva in automatico (max 5 per messaggio). Mai su merge, produzione, soldi, legale, invii, cancellazioni o scelte A/B

Le chat nate da un handoff partono già accese. Senza persona (`claude -p`, task programmati): solo avvisi.

**Regolazioni** (variabili d'ambiente): `FAZEN_MEMORY_YELLOW_TOKENS`, `FAZEN_MEMORY_RED_TOKENS`, `FAZEN_MEMORY_AUTO=0` (solo avvisi, niente handoff forzato).
```

Then one line for this chat: Fazen Memory off → "💡 Spenta in questa chat: `/fazenmemory` per accenderla."; a code word miss or a long chat → "🔴 Passo a una chat nuova adesso?"; otherwise "✅ Tutto a posto."

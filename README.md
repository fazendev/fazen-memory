# Fazen Memory

Le chat lunghe di Claude Code passano da sole a una chat nuova, senza perdere regole, correzioni o dati.
Fork di [active-memory](https://github.com/Klopyy/active-memory) 0.2.6 (MIT).

## Comandi

| Comando | Cosa fa |
|---|---|
| `/fazenmemory [off\|status]` | Accende Fazen Memory nella chat (code word **Si Fratello!**, checkpoint, handoff automatico, auto-continua) |
| `/fmcodeword [frase\|off]` | Cambia o spegne la code word |
| `/fmcheckpoint` | Riepilogo + salute 🟢🟡🔴 |
| `/fmhandoff [file]` | Handoff + nuova chat nella stessa cartella in modalità auto |
| `/fmhelp` | Guida |

Soglie (solo con Fazen Memory accesa): 🟡 20 scambi o 300k token → checkpoint; 🔴 35 scambi, 450k token
o code word mancante (in una chat già lunga) → handoff automatico, una volta per chat.

## Installazione

```powershell
.\install.ps1
```

Crea le junction `~/.claude/skills/<skill>` e `~/.claude/fazen-memory/{hooks,tests}` verso questa repo:
modificare i file qui li aggiorna per tutte le chat. Gli hook vanno registrati in `~/.claude/settings.json`:

```json
"UserPromptSubmit": [{ "hooks": [{ "type": "command", "timeout": 15,
  "command": "C:/PROGRA~1/PYTHON~1/python.exe \"~/.claude/fazen-memory/hooks/on_prompt.py\"" }] }],
"Stop": [{ "hooks": [{ "type": "command", "timeout": 15,
  "command": "C:/PROGRA~1/PYTHON~1/python.exe \"~/.claude/fazen-memory/hooks/on_stop.py\"" }] }]
```

Path corto senza spazi di Python 3.11: funziona sia in bash sia in PowerShell.

## Test

```powershell
python tests\test_hooks.py
```

Stato per chat (non versionato): `~/.claude/fazen-memory/sessions/`.

# Fazen Memory

Long Claude Code chats drift: rules given early get forgotten, corrections get undone. Fazen Memory
notices when a chat is getting too long and moves the work to a fresh chat on its own, with a handoff
file that carries every rule, correction and exact value over.

A fork of [active-memory](https://github.com/Klopyy/active-memory) 0.2.6 (MIT).

## What it does

Fazen Memory is **off** in every chat until you type `/fazenmemory`. When it is on:

- **Code word.** Claude starts every reply with a fixed phrase (default **Yes Brother!** in English,
  **Si Fratello!** in Italian). The first reply without it shows the chat is losing track.
- **Checkpoint** 🟡 at 20 exchanges or ~300k context tokens: a compact recap at the end of a reply.
- **Automatic handoff** 🔴 at 35 exchanges, ~450k context tokens, or a missing code word in a chat
  that is already long: Claude writes a complete handoff file and opens a new chat in the same folder,
  in auto mode, once per chat.
- **Auto-continue.** No more "Shall I continue with step 2?": an obvious continuation question is
  answered yes automatically (at most 5 times per message). Never for merge, production, money, legal,
  sending anything, deleting, or "A or B?" choices.

Chats opened by a handoff start with Fazen Memory already on. Without a person in the chat
(`claude -p`, scheduled tasks) it only warns.

## Install

Requires Claude Code 2.1.271 or later, bash (on Windows, Git Bash) and Python 3.8+ (`python3`,
`python` or `py`).

In a Claude Code session (2.1.275 or later):

```text
/plugin install fazen-memory --marketplace fazendev/fazen-memory
```

Or from your shell (2.1.292 or later):

```bash
claude plugin install fazen-memory --marketplace fazendev/fazen-memory
```

On older versions, add the marketplace first, then install:

```bash
claude plugin marketplace add fazendev/fazen-memory
claude plugin install fazen-memory@fazen-memory
```

The desktop app reads the same settings as the terminal: once the marketplace is added, the plugin
also appears under **+ > Plugins > Add plugin** in a Code session.

## Commands

| Command | What it does |
|---|---|
| `/fazenmemory [off\|status]` | Turns Fazen Memory on in this chat, off, or shows its status |
| `/fmcodeword [phrase\|off]` | Changes the code word or turns it off |
| `/fmcheckpoint` | Compact recap + health 🟢🟡🔴 |
| `/fmhandoff [file]` | Handoff file + new chat in the same folder in auto mode (`file` = the file only) |
| `/fmhelp` | Guide, in your language |

Each command also works with the plugin prefix, e.g. `/fazen-memory:fazenmemory`.

## Settings

Asked when you enable the plugin; change them later in `/config` or under **Configure options** in
`/plugin`.

| Option | Values | Default |
|---|---|---|
| Language | `auto`, `english`, `italian` | `auto`: Claude Code's `language` setting, otherwise your system language |
| Default code word | any phrase | empty: **Yes Brother!** in English, **Si Fratello!** in Italian |

Environment variables: `FAZEN_MEMORY_YELLOW_TOKENS` (300000), `FAZEN_MEMORY_RED_TOKENS` (450000),
`FAZEN_MEMORY_AUTO=0` (warnings only, never a forced handoff).

## Privacy

Everything stays on your machine. Per-chat state (on/off, exchange count, code word) is saved in the
plugin's data folder (`~/.claude/plugins/data/`). Handoff files go to
`<project>/.claude/handoffs/`, and Fazen Memory adds that folder to `.gitignore` so they are not
committed.

## Development

```bash
python tests/test_hooks.py          # hook tests
claude plugin validate .            # manifest check
claude --plugin-dir .               # load this checkout for one session
```

## License

MIT. See [LICENSE](LICENSE).

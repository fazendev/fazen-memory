---
name: fmhandoff
description: "Fazen Memory handoff. Use when the user types \"/fmhandoff\" (or \"/fmhandoff auto\"), asks to \"move to a new chat\", \"passa a una nuova chat\", \"fai l'handoff\", \"continua in una chat nuova\", or when a [fazen-memory] hook note says a red signal fired (code word missing, ~35 exchanges, context too large). It reads the whole chat in four passes, writes a complete handoff file in the project, then (AUTO mode) starts a new chat in the same folder in auto permission mode, switches to it and gives the user its link. Also use it when a message or file starts with \"# Fazen Memory handoff\" or \"Fazen Memory resume\"."
metadata:
  version: "1.0.0"
  forked-from: "active-memory 0.2.6 (MIT, Klopyy)"
---

# Fazen Memory: handoff

Write a handoff file so complete that a brand-new chat with no access to this one continues at full quality from its first reply: same rules, same style, same exact data, same next step, none of the corrected mistakes. Then, in AUTO mode, open that new chat yourself and move the user there.

## Mode

- **AUTO** (default): when a `[fazen-memory]` hook note asked for it, when the user typed `/fmhandoff` or `/fmhandoff auto`, or asked in words to move to a new chat. Do the four passes, write the file, then run **Start the new chat**.
- **FILE**: only when the user typed `/fmhandoff file` or asked only for the file. Do the four passes, write the file, show the manual guide at the end.

Never stop in the middle of a multi-step tool run to hand off: finish the current step, then hand off. In AUTO mode ask the user nothing except real conflicts (Pass 2); everything else goes into section 12.

## Pass 1: Scan (message 1 → last)

Go through the conversation **from the very first message to the last**, in order. Do not start from the recent end. For every message, record anything that belongs in sections 1-13. Always important:

- Every instruction about how Claude should behave or write, even if said once in passing.
- Every time the user corrected Claude: what Claude did, what the user wanted instead.
- Every rejected idea or replaced decision, with the reason when one was given.
- Every exact value: numbers, prices, dates, IDs, names, spellings, file names, paths, URLs, versions, commands, commit SHAs, branch names.
- Every file, document, artifact, or piece of code created or changed, and its latest state.
- The user's own words for things (nicknames, abbreviations, project names).
- Anything uploaded that the new chat will need again.

Copy rules and data **word for word**. Summarize only discussion. Skip what the repo already records durably (CLAUDE.md, committed code, memory files): reference it by path instead of copying it.

## Pass 2: Reconcile

- For each topic, the **latest** statement from the user wins. Put the replaced version in section 7 with an arrow: `old → new`.
- Separate what the **user** decided from what Claude only **suggested**. Unaccepted suggestions are not decisions.
- Merge duplicates. Keep the most exact wording.
- **Conflicts:** if two statements disagree and the chat never settles which wins, ask the user 1-3 short numbered questions with the candidate answers, including "skip, flag it in the file". Wait for the reply. If there are no real conflicts, ask nothing.

## Pass 3: Gap check

Pretend to be a fresh Claude reading only the draft. For each section ask: "What would I still have to ask, or what could I get wrong?"

- Fill the gap from the chat if the answer is there; otherwise list it under section 12. Never invent it.
- Section 11 names one concrete next action, not "continue the work".
- A reader could reproduce the style from section 3 alone.
- In a git repo, record in section 10: branch, HEAD short SHA, and `git status --short` (uncommitted files). Run the commands; do not guess.

## Pass 4: Self-audit

- [ ] Title line and headings 0-13 match the template exactly, in order. Empty sections say "None."
- [ ] Section 5 lists every correction as a table row, even small ones.
- [ ] Every hard rule, correction, number, price and name matches the chat exactly.
- [ ] Nothing depends on the old chat ("as discussed above").
- [ ] Secrets (passwords, API keys, tokens, card numbers) are replaced with `[secret removed: re-enter it]`.
- [ ] Files that must be attached again are in section 13.
- [ ] Section 0 is unchanged from the template, placeholders filled.

Fix anything unchecked, then write the audit line at the bottom. Do not add a separate checklist to the file.

## The file

Use exactly this structure. Replace everything in `<angle brackets>`. Content in the chat's main language; headings stay as written. Compact lines, one fact per bullet, tables for data with more than 3 rows. Inline small critical code (up to ~50 lines); list larger things in section 13 or reference their path.

````markdown
# Fazen Memory handoff: <project or chat title>

**Handoff #<n>** · <YYYY-MM-DD> · Folder: `<absolute path of the working folder>` · Lineage: <#1 (date): one-line summary>; <#2 …>

## 0. Instructions for Claude (read first)

You are continuing work from a previous chat. That chat is gone for you; this file is the complete context and the source of truth.

1. Read this whole file before replying.
2. Follow sections 3 (Style), 4 (Hard rules) and 5 (Corrections) in every reply, for the rest of this chat. They override your defaults.
3. Use the values in section 8 exactly. Never round, re-estimate, or "correct" them.
4. Do not suggest anything listed in section 7 (Changed / rejected) again unless the user brings it up.
5. Code word: <Start every reply with exactly "PHRASE" | None active. If the user types /fmcodeword, start every reply with the phrase they choose (default "Si Fratello!")>.
6. Start mode: <AUTONOMOUS: reply with at most 5 lines (goal, current state, next step), then start the next step (section 11) in the same turn without waiting | WAIT: reply with at most 5 lines (goal, current state, next step), ask the questions in section 12, end with "Pronto a continuare con <next step>?" and wait for the go>. In both modes, stop and ask before anything that is the user's decision: merge, production deploy, spending money, legal, sending anything external.
7. Fazen Memory is on in this chat. Auto-continue: never ask permission for the obvious next step of the plan ("Posso continuare con…?", "Procedo?"); do it. Ask only for the user's decisions (merge, production, money, legal, sending anything external, deleting), a genuinely open choice, or data you cannot find.
8. Previous chat: <ARCHIVE session `<previous session id>` once your first reply is out (the user asked for old chats to be archived after a handoff) | KEEP (this chat runs in a terminal tab of the previous one: archiving it would close this chat)>.

## 1. Mission
- **Goal:** <what is being built or solved>
- **Done looks like:** <how the user will judge it finished>
- **Why it matters / context:** <one line, if stated>

## 2. About the user (as relevant to this work)
- <role, domain, tools, audience>

## 3. Style & communication
- **Language:** <…>
- **Tone:** <…>
- **Reply length:** <…>
- **Formatting:** <…>
- **Working style:** <…>
- **Avoid:** <…>

## 4. Hard rules (word for word)
1. "<exact rule>" <(context, if needed)>

## 5. Corrections log
| # | Claude did | The user wanted |
|---|---|---|
| 1 | <mistake> | <correction, exact> |

## 6. Decisions
| Decision | Why |
|---|---|
| <final choice> | <reason, or "user's call"> |

## 7. Changed / rejected
- <old> → <new> (<reason>)
- ❌ <rejected idea> (<reason>)

## 8. Data & facts (exact)
<tables or bullets of numbers, prices, dates, IDs, measurements, specs>

## 9. People, terms & names
- **People:** <name: role>
- **Terms & nicknames:** <term = meaning>
- **Names in use:** <file names, variables, commands, exact spellings>

## 10. Work state
- **Git:** <branch · HEAD sha · uncommitted files, or "not a git repo">

| Item | Status | Version / location | Notes |
|---|---|---|---|
| <file, feature> | <final / draft / not started> | <path, link> | <what's left> |

## 11. Next steps
1. **Next action:** <one concrete step>
2. <then…>

## 12. Open questions ⚠️
- <unresolved item, with the candidate answers>
<or "None.">

## 13. Re-attach checklist
- [ ] <file name>: <why the new chat needs it>
<or "Nothing to attach.">

---
<sub>Audit: 13/13 sections · <N> rules · <N> corrections · <N> data points · secrets removed: <yes/none found> · generated by Fazen Memory</sub>
````

In AUTO mode set section 0 point 6 to **AUTONOMOUS** unless the chat was waiting on a user decision that blocks the next step; then use **WAIT**.

## Chained handoffs

If this chat itself started from a Fazen Memory (or active-memory) handoff file: start from that file, do not rebuild from zero, increase the number (`#2`, `#3`…), apply the four passes to the messages since it was loaded, update every section, move replaced items to section 7, and add one line to **Lineage**.

## Save the file

1. Working folder = the session's current working directory. If it is a scratch / "No folder" workspace (deleted with the session), the working folder is instead the real project folder the work in this chat touched (e.g. the repo whose files were edited); if there is none, save the file, show it with SendUserFile, and use the manual guide below.
2. Path: `<working folder>/.claude/handoffs/handoff-<project-name>.md` (lowercase, hyphens). Same file for chained handoffs (the lineage keeps the history).
3. In a git repo, make sure the handoff is not committed: `git check-ignore -q .claude/handoffs/x`; if it is not ignored, add the line `.claude/handoffs/` to `.gitignore` (only that folder: repos often commit `.claude/settings.json` or project skills on purpose).
4. Verify the file exists and is complete (Read its last lines: the audit line must be there).

## Start the new chat (AUTO mode)

Do every step; verify instead of assuming. Use the session-management tools, which are deferred: load them first.

1. **Load tools.** `ToolSearch` with `select:mcp__ccd_session_mgmt__hand_off_to_session,mcp__ccd_session_mgmt__start_session,mcp__ccd_session_mgmt__set_session_permission_mode,mcp__ccd_session_mgmt__set_session_title,mcp__ccd_session_mgmt__get_session,mcp__ccd_window__open_session_in,mcp__terminal__run_in_terminal,mcp__terminal__read_terminal,mcp__ccd_session__spawn_task`. Use only what comes back; never call a tool that did not load.
2. **Resume message** (the first message of the new chat), in the chat's language:
   ``Fazen Memory resume: leggi per intero `<absolute path of the handoff file>` e segui la sezione 0. Cartella di lavoro: `<absolute working folder>`.``
   Keep this exact wording and the backticks around the path: the Fazen Memory hook reads the path from it to re-arm the code word in the new chat.
3. **Primary path: a session-starting tool loaded** (`hand_off_to_session`, else `start_session`). Read its schema and fill it: same working folder as this session, **no new worktree** when the schema offers that choice (uncommitted work must stay visible), title `<project> · handoff #<n>`, permission mode `auto` if the schema has it, the resume message as the prompt.
   1. If the mode was not set at start: `set_session_permission_mode(<new id>, "auto")`. The app may show the user an approval card; that is expected.
   2. `set_session_title` if the title was not set at start.
   3. `open_session_in(<new id>, "focus")`; if it is refused, try `"split"`; if that is refused too, just give the link.
   4. **Verify** with `get_session(<new id>)`: it exists, is in the same folder, `permissionMode` is `auto`. Report what is not true instead of claiming it.
4. **Terminal path (zero clicks; verified live 2026-10-13): no session-starting tool, `run_in_terminal` loaded.** A Claude Code session in a tab of the app's Terminal panel, in the same folder, no worktree.
   1. Read the app's own Claude Code executable with Bash: `echo "$CLAUDE_CODE_EXECPATH"` (same version as the app, so it supports the same models; the npm `claude` can be too old). If it is empty, use `claude`.
   2. `run_in_terminal` without `cwd` (the tool refuses folders outside this session) and with `command`, one line, printable ASCII only, **no backticks, no `$variables`**:
      `Set-Location '<working folder>'; <exe path> --model <this chat's model id> --permission-mode auto 'Fazen Memory resume: leggi per intero <absolute path of the handoff file> e segui la sezione 0. Cartella di lavoro: <working folder>.'`
      (the hook also reads the path without backticks). Title: `<project> #<n>`.
   3. **Verify** with `read_terminal` (wait 30-60s): the header shows the right folder, the model, `Claude Max` (or the account's plan) and `auto mode on`, and the session starts reading the handoff file. If the header shows API billing, a version error or a login prompt, stop the tab and report it instead of claiming the handoff worked.
   4. Edits inside `~/.claude` still ask for approval in that session even in auto mode (protected folder): say so if the next step touches it.
5. **Fallback: `spawn_task` loaded.** The chip starts a new chat in its own worktree, which does not see uncommitted changes.
   1. If `git status --short` shows uncommitted changes, tell the user in one line which files are uncommitted and ask whether to commit them first (committing is their call). Their answer comes before the chip.
   2. `spawn_task` with `cwd` = the working folder, `title` = `Continua <project> (handoff #<n>)`, `tldr` = why (chat too long, handoff #n ready), `prompt` = the resume message plus: `Prima azione: passa questa sessione in modalità auto con set_session_permission_mode("self", "auto").`
   3. The user needs one click on the chip. Say so plainly; do not claim the new chat is running.
6. **No path available:** use the manual guide below.
7. Do not archive this chat yourself: you cannot know when the new chat is really running (with the chip it starts only when the user clicks). Section 0 point 8 tells the new chat to archive this one: ARCHIVE with this session's id (`get_session("self")`) on the primary and chip paths; KEEP on the Terminal path (the new chat lives in a terminal tab of this chat, and archiving this chat would end it).
8. **This chat stops working on the task.** From here on the new chat owns the folder: two chats editing the same files collide. If the user writes here again about the task, remind them in one line that the work moved (with the link) and do not edit files, unless they explicitly ask to keep working here.

## Final reply (AUTO mode)

Start with the code word if one is active. Then, short, in the user's language:

```
🔁 **Siamo passati a questa nuova chat:** [<title>](#<new session id>) · <link from get_session>
- Modalità: auto <✅ verificata | ⚠️ <what get_session says>>
- Handoff: `<path>` (#<n>)
- Riparte da: <next step from section 11>
Questa chat la archivia la nuova appena è partita.
```
(Terminal path: "Questa chat resta aperta: ospita il tab della nuova.")

In the Terminal path the first line is: `🔁 **Siamo passati a questa nuova chat:** [<title>](#terminal/<tab_id>) (tab del Terminale, cartella `<working folder>`)`.
In the chip fallback replace the first line with: `🔁 **Handoff #<n> pronto.** Clicca il chip "<title>" qui sotto: apre la nuova chat e riparte da sola.`

## Manual guide (FILE mode or no tools)

```
✅ **Handoff pronto:** `<path>`
1. Apri una nuova chat nella stessa cartella e scegli la modalità auto.
2. Invia: Fazen Memory resume: leggi per intero `<path>` e segui la sezione 0.
```

## Resuming (in the new chat)

When a message starts with `Fazen Memory resume`, or a file/paste starts with `# Fazen Memory handoff` (or `# active-memory handoff`):

1. Read the entire file before replying. Its section 0 applies for the rest of the chat; sections 3, 4, 5 are binding, section 8 is exact data.
2. If section 0 names a code word, start this reply and every later one with it. The hooks re-arm it on their own from the resume message; only when the file was attached or pasted some other way, mention in one line that `/fmcodeword <phrase>` turns the automatic check back on.
3. Follow the start mode in section 0 point 6: AUTONOMOUS → 5-line summary, then start the next step in the same turn; WAIT → 5-line summary, questions from section 12, "Pronto a continuare con <next step>?", then wait.
4. Mention any files from section 13 that are not reachable.
5. Section 0 point 8 says ARCHIVE: right after your first reply, load `mcp__ccd_session_mgmt__get_session` and `mcp__ccd_session_mgmt__archive_session` (ToolSearch). Archive only if `get_session("self")` works (this is a Code-tab chat, not a terminal CLI session) and the session to archive is the one named in point 8 or this chat's `parentSessionId`, and it is not running. Pass the reason "Handoff #<n>: il lavoro continua qui". One line to the user: archived, or why not. Never archive any other session.

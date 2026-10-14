import json, os, subprocess, sys, tempfile, uuid

sys.stdout.reconfigure(encoding="utf-8")  # Windows console is cp1252; hook messages carry emoji

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks")
# Isolated state: the hooks write where an installed plugin would, in a throwaway folder.
DATA = tempfile.mkdtemp(prefix="fm_data_")
os.environ["CLAUDE_PLUGIN_DATA"] = DATA
STATE = os.path.join(DATA, "sessions")
os.makedirs(STATE)
fails = []
# Baseline: an attended chat (test 19 changes it), plugin language Italian (test 21 changes it).
os.environ["CLAUDE_CODE_SESSION_ATTENDED"] = "1"
os.environ["CLAUDE_PLUGIN_OPTION_LANGUAGE"] = "italian"


def run(script, payload):
    p = subprocess.run([sys.executable, os.path.join(HOOKS, script)], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, timeout=30)
    assert p.returncode == 0, p.stderr
    out = p.stdout.decode("utf-8").strip()
    return json.loads(out) if out else {}


BASE = 120000  # fixed overhead of a real chat (system prompt, tools, skills, MCP): seen ~116k live


def transcript(reply, tokens=1000, base=BASE):
    """A chat whose first call costs `base` (the fixed overhead) and whose latest call carries
    `tokens` of conversation on top of it."""
    path = os.path.join(tempfile.gettempdir(), "fm_t_%s.jsonl" % uuid.uuid4().hex)
    rows = [
        {"type": "user", "message": {"role": "user", "content": "inizio"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "ok"}],
                                          "usage": {"input_tokens": base}}},
        {"type": "user", "message": {"role": "user", "content": "ciao"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": reply}],
                                          "usage": {"input_tokens": 1, "cache_creation_input_tokens": 0,
                                                    "cache_read_input_tokens": base + tokens - 1}}},
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> %s" % detail))
    if not cond:
        fails.append(name)


def new_session():
    return "test-" + uuid.uuid4().hex


def on_session():
    """A chat where Fazen Memory is on but no code word is set."""
    sid = new_session()
    with open(os.path.join(STATE, sid + ".json"), "w", encoding="utf-8") as f:
        json.dump({"enabled": True, "turns": 0, "codeword": None}, f)
    return sid


# 1. codeword set via prompt, reply with it -> no output
s = new_session()
t = transcript("Si Fratello! tutto ok")
run("on_prompt.py", {"session_id": s, "prompt": "/fmcodeword", "transcript_path": t})
out = run("on_stop.py", {"session_id": s, "transcript_path": t, "last_assistant_message": "Si Fratello! tutto ok"})
check("codeword present -> silent", out == {}, out)

# 2a. miss in a fresh chat (e.g. first reply after a handoff) -> warning only, no handoff loop
t2 = transcript("Ecco il codice")
out = run("on_stop.py", {"session_id": s, "transcript_path": t2, "last_assistant_message": "Ecco il codice"})
check("fresh chat miss -> warn, no block", "decision" not in out and "code word" in out.get("systemMessage", ""), out)

# 2b. first miss in a long chat (>= 10 exchanges) -> warning only: one slip is not drift
for _ in range(9):
    run("on_prompt.py", {"session_id": s, "prompt": "vai", "transcript_path": t2})
out = run("on_stop.py", {"session_id": s, "transcript_path": t2, "last_assistant_message": "Ecco il codice"})
check("first long-chat miss -> warn, no block", "decision" not in out and "code word" in out.get("systemMessage", ""), out)

# 2c. the next prompt reminds Claude of the rules, without ever sending the phrase
out = run("on_prompt.py", {"session_id": s, "prompt": "vai", "transcript_path": t2})
ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
check("miss -> reminder on next prompt", "code word" in ctx, out)
check("reminder does not leak phrase", "Fratello" not in ctx, out)
out = run("on_prompt.py", {"session_id": s, "prompt": "vai", "transcript_path": t2})
check("reminder only once", "code word" not in out.get("hookSpecificOutput", {}).get("additionalContext", ""), out)

# 2d. second miss in the long chat -> block + systemMessage, phrase never leaked to Claude
out = run("on_stop.py", {"session_id": s, "transcript_path": t2, "last_assistant_message": "Ecco il codice"})
check("codeword missing again -> block", out.get("decision") == "block", out)
check("reason does not leak phrase", "Fratello" not in out.get("reason", ""), out)
check("systemMessage shown", "code word" in out.get("systemMessage", ""), out)

# 3. third miss -> no second block (once per chat), warning only
out = run("on_stop.py", {"session_id": s, "transcript_path": t2, "last_assistant_message": "Ecco il codice"})
check("third miss -> no re-block", "decision" not in out and "systemMessage" in out, out)

# 4. stop_hook_active -> nothing (anti-loop)
out = run("on_stop.py", {"session_id": new_session(), "stop_hook_active": True, "transcript_path": t2})
check("stop_hook_active -> silent", out == {}, out)

# 5. red tokens (conversation, overhead excluded) without codeword -> block
s5 = on_session()
t5 = transcript("risposta", tokens=720000)
out = run("on_stop.py", {"session_id": s5, "transcript_path": t5, "last_assistant_message": "risposta"})
check("red tokens -> block", out.get("decision") == "block" and "720k" in out.get("reason", ""), out)

# 6. below red tokens -> silent
s6 = on_session()
out = run("on_stop.py", {"session_id": s6, "transcript_path": transcript("x", tokens=690000),
                          "last_assistant_message": "x"})
check("below red -> silent", out == {}, out)

# 6b. the fixed overhead does not count: 750k in the window, of which 300k fixed -> 450k of
#     conversation, under red (the old total-context measure handed off here)
out = run("on_stop.py", {"session_id": on_session(), "transcript_path": transcript("x", tokens=450000, base=300000),
                          "last_assistant_message": "x"})
check("fixed overhead excluded -> no red", out == {}, out)

# 7. yellow tokens on prompt -> checkpoint note once
s7 = on_session()
t7 = transcript("x", tokens=460000)
out = run("on_prompt.py", {"session_id": s7, "prompt": "vai", "transcript_path": t7})
ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
check("yellow tokens -> checkpoint note", "fmcheckpoint" in ctx, out)
out = run("on_prompt.py", {"session_id": s7, "prompt": "vai", "transcript_path": t7})
check("yellow note only once", out == {}, out)

# 8. 35 turns -> block on stop
s8 = on_session()
t8 = transcript("x")
for _ in range(35):
    run("on_prompt.py", {"session_id": s8, "prompt": "vai", "transcript_path": t8})
out = run("on_stop.py", {"session_id": s8, "transcript_path": t8, "last_assistant_message": "x"})
check("35 turns -> block", out.get("decision") == "block" and "35 exchanges" in out.get("reason", ""), out)

# 9. manual /fmhandoff earlier -> red does not re-block, single warning
s9 = on_session()
t9 = transcript("x", tokens=720000)
run("on_prompt.py", {"session_id": s9, "prompt": "/fmhandoff", "transcript_path": t9})
out = run("on_stop.py", {"session_id": s9, "transcript_path": t9, "last_assistant_message": "x"})
check("after manual handoff -> no block, warn", "decision" not in out and "fmhandoff" in out.get("systemMessage", ""), out)
out = run("on_stop.py", {"session_id": s9, "transcript_path": t9, "last_assistant_message": "x"})
check("red warning only once", out == {}, out)

# 10. FAZEN_MEMORY_AUTO=0 -> warn, never block
os.environ["FAZEN_MEMORY_AUTO"] = "0"
out = run("on_stop.py", {"session_id": on_session(), "transcript_path": t9, "last_assistant_message": "x"})
check("AUTO=0 -> no block", "decision" not in out and "systemMessage" in out, out)
del os.environ["FAZEN_MEMORY_AUTO"]

# 11. /fmcodeword off and garbage stdin
run("on_prompt.py", {"session_id": s, "prompt": "/fmcodeword off", "transcript_path": t2})
check("codeword off stored", json.load(open(os.path.join(STATE, s + ".json"), encoding="utf-8"))["codeword"] is None)
p = subprocess.run([sys.executable, os.path.join(HOOKS, "on_stop.py")], input=b"not json", capture_output=True)
check("garbage stdin -> exit 0 silent", p.returncode == 0 and not p.stdout.strip(), p)

# 12. resume message re-arms the code word from the handoff file (path with spaces, in backticks)
hdir = os.path.join(tempfile.gettempdir(), "fm test dir")
os.makedirs(hdir, exist_ok=True)
hfile = os.path.join(hdir, "handoff-x.md")
with open(hfile, "w", encoding="utf-8") as f:
    f.write('# Fazen Memory handoff: x\n\n5. Code word: Start every reply with exactly "Agli ordini!".\n')
s12 = new_session()
run("on_prompt.py", {"session_id": s12, "prompt": "Fazen Memory resume: leggi per intero `%s` e segui la sezione 0." % hfile})
st12 = json.load(open(os.path.join(STATE, s12 + ".json"), encoding="utf-8"))
check("resume re-arms codeword", st12.get("codeword") == "Agli ordini!", st12)
with open(hfile, "w", encoding="utf-8") as f:
    f.write('5. Code word: None active. If the user types /fmcodeword ... (default "Si Fratello!").\n')
s12b = new_session()
run("on_prompt.py", {"session_id": s12b, "prompt": "Fazen Memory resume: leggi per intero `%s`" % hfile})
st12b = json.load(open(os.path.join(STATE, s12b + ".json"), encoding="utf-8"))
check("resume with no code word -> stays off", not st12b.get("codeword"), st12b)

# 13. big transcript (> tail window): fast, and still finds the reply start
big = os.path.join(tempfile.gettempdir(), "fm_big.jsonl")
filler = json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": "x" * 5000}]}})
with open(big, "w", encoding="utf-8") as f:
    f.write(json.dumps({"type": "user", "message": {"content": "inizio"}}) + "\n")
    f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "ok"}],
                        "usage": {"input_tokens": BASE}}}) + "\n")
    for _ in range(4000):  # ~20 MB of old history
        f.write(filler + "\n")
    f.write(json.dumps({"type": "user", "message": {"content": "vai"}}) + "\n")
    f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Ecco"}],
                        "usage": {"input_tokens": BASE + 720000}}}) + "\n")
s13 = new_session()
run("on_prompt.py", {"session_id": s13, "prompt": "/fmcodeword", "transcript_path": big})
import time as _t
t0 = _t.time()
out = run("on_stop.py", {"session_id": s13, "transcript_path": big, "last_assistant_message": "Ecco"})
dt = _t.time() - t0
check("big transcript: miss + red detected", out.get("decision") == "block" and "720k" in out.get("reason", "")
      and "code word" in out.get("systemMessage", ""), out)
check("big transcript: under 3s (%.2fs)" % dt, dt < 3, dt)
os.remove(big)

# 14. optional: a real transcript passed as argv[1] -> print its context size, compare with get_usage
sys.path.insert(0, HOOKS)
import state  # noqa
if len(sys.argv) > 1:
    n = state.context_tokens(sys.argv[1])
    print("real transcript context tokens:", n, "of which conversation:", state.conversation_tokens(sys.argv[1]))
    check("real transcript tokens > 0", n > 0, n)

def state_of(sid):
    return json.load(open(os.path.join(STATE, sid + ".json"), encoding="utf-8"))


def note_of(out):
    return out.get("hookSpecificOutput", {}).get("additionalContext", "")


# 15. off by default: a new chat without /fazenmemory gets nothing, even past the red marks
s15 = new_session()
t15 = transcript("x", tokens=720000)
for _ in range(36):
    out = run("on_prompt.py", {"session_id": s15, "prompt": "vai", "transcript_path": t15})
check("off by default: no nudges", out == {} and not state_of(s15).get("enabled"), state_of(s15))
out = run("on_stop.py", {"session_id": s15, "transcript_path": t15, "last_assistant_message": "Procedo col punto 2?"})
check("off by default: stop silent", out == {}, out)

# 16. /fazenmemory turns it on with "Si Fratello!"; accents tolerated; off turns everything off
s16 = new_session()
run("on_prompt.py", {"session_id": s16, "prompt": "/fazenmemory"})
st16 = state_of(s16)
check("/fazenmemory -> on + Si Fratello!", st16.get("enabled") and st16.get("codeword") == "Si Fratello!", st16)
t16 = transcript("Sì Fratello! fatto")
out = run("on_stop.py", {"session_id": s16, "transcript_path": t16, "last_assistant_message": "Sì Fratello! fatto"})
check("accented 'Si' still counts", out == {}, out)
run("on_prompt.py", {"session_id": s16, "prompt": "/fazenmemory off"})
check("/fazenmemory off", not state_of(s16).get("enabled") and not state_of(s16).get("codeword"), state_of(s16))

# 17. resume message turns it on and carries the phrase
with open(hfile, "w", encoding="utf-8") as f:
    f.write('5. Code word: Start every reply with exactly "Si Fratello!".\n')
s17 = new_session()
run("on_prompt.py", {"session_id": s17, "prompt": "Fazen Memory resume: leggi per intero `%s`" % hfile})
check("resume -> on + carried phrase", state_of(s17).get("enabled") and state_of(s17).get("codeword") == "Si Fratello!",
      state_of(s17))
s17b = new_session()
run("on_prompt.py", {"session_id": s17b, "prompt": "Fazen Memory resume: read in full `%s` and follow section 0." % hfile})
check("English resume -> on + carried phrase",
      state_of(s17b).get("enabled") and state_of(s17b).get("codeword") == "Si Fratello!", state_of(s17b))


# 18. auto-continue on obvious continuation questions
def stop_with(sid, msg, active=False):
    t = transcript("Si Fratello! " + msg)
    return run("on_stop.py", {"session_id": sid, "transcript_path": t, "stop_hook_active": active,
                              "last_assistant_message": "Si Fratello! " + msg})


s18 = new_session()
run("on_prompt.py", {"session_id": s18, "prompt": "/fazenmemory"})
out = stop_with(s18, "Punto 1 fatto, test verdi.\n\nPosso continuare con il punto 2?")
check("obvious question -> auto yes", out.get("decision") == "block" and "YES" in out.get("reason", ""), out)
for msg in ("Step 1 done, tests green.\n\nShall I proceed with step 2?", "Done. Want me to carry on with the next step?"):
    out = stop_with(s18, msg)
    check("English obvious question -> auto yes", out.get("decision") == "block", [msg, out])
cases = [
    ("choice", "Procedo con A o con B?"),
    ("two questions", "Ti va bene il nome? Procedo con il punto 2?"),
    ("gated deploy", "Build verde. Procedo con il deploy in produzione?"),
    ("gated merge", "Review ok. Posso continuare con il merge della PR?"),
    ("not a continuation", "Che colore preferisci per il bottone?"),
    ("no question", "Fatto, tutto verde."),
    ("en choice", "Shall I proceed with A or B?"),
    ("en gated deploy", "Build is green. Shall I proceed with the production deploy?"),
    ("en gated delete", "Shall I proceed and remove the old branch?"),
    ("en gated payment", "Shall I continue and buy the domain?"),
    ("en not a continuation", "Which color do you prefer for the button?"),
]
for name, msg in cases:
    check("no auto yes: " + name, "decision" not in stop_with(s18, msg), msg)
for _ in range(10):  # chained continues are capped per user message
    stop_with(s18, "Ok. Vado avanti con il prossimo punto?", active=True)
check("cap per message", state_of(s18)["auto_continues"] == 5, state_of(s18))
run("on_prompt.py", {"session_id": s18, "prompt": "ok"})
check("cap resets on user message", state_of(s18)["auto_continues"] == 0, state_of(s18))

# 19. unattended (claude -p, scheduled): no forced handoff and no automatic yes, only warnings
os.environ["CLAUDE_CODE_SESSION_ATTENDED"] = "0"
s19 = new_session()
run("on_prompt.py", {"session_id": s19, "prompt": "/fazenmemory"})
out = run("on_stop.py", {"session_id": s19, "transcript_path": transcript("Si Fratello! x", tokens=720000),
                          "last_assistant_message": "Si Fratello! Procedo con il punto 2?"})
check("unattended -> warn only", "decision" not in out and "systemMessage" in out, out)
os.environ["CLAUDE_CODE_SESSION_ATTENDED"] = "1"

import shutil
shutil.rmtree(hdir, ignore_errors=True)
# 20. the plugin launcher finds a working Python and passes the hook its stdin
bash = shutil.which("bash")
if bash:
    s20 = new_session()
    p = subprocess.run([bash, os.path.join(HOOKS, "run.sh"), "on_prompt.py"],
                       input=json.dumps({"session_id": s20, "prompt": "/fazenmemory"}).encode("utf-8"),
                       capture_output=True, timeout=60)
    check("run.sh launcher -> hook ran", p.returncode == 0 and state_of(s20).get("enabled") is True,
          [p.returncode, p.stderr[-300:]])
else:
    print("SKIP run.sh launcher (no bash)")

# 21. language: plugin option, Claude Code's `language` setting, custom default code word
def turn_on(sid):
    return run("on_prompt.py", {"session_id": sid, "prompt": "/fazenmemory"})


s21 = new_session()
out = turn_on(s21)
ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
check("turn-on note names phrase + language", '"Si Fratello!"' in ctx and "Italian" in ctx, ctx)
out = run("on_stop.py", {"session_id": s21, "last_assistant_message": "Ok fatto."})
check("Italian miss warning", "non è iniziata" in out.get("systemMessage", ""), out)
out = run("on_prompt.py", {"session_id": s21, "prompt": "ciao"})
check("no phrase note in later turns", "Si Fratello" not in json.dumps(out), out)

os.environ["CLAUDE_PLUGIN_OPTION_LANGUAGE"] = "english"
s21 = new_session()
turn_on(s21)
check("english -> Yes Brother!", state_of(s21).get("codeword") == "Yes Brother!", state_of(s21))
out = run("on_stop.py", {"session_id": s21, "last_assistant_message": "Done."})
check("English miss warning", "did not start" in out.get("systemMessage", ""), out)
s21 = new_session()
run("on_prompt.py", {"session_id": s21, "prompt": "/fmcodeword"})
check("/fmcodeword default follows language", state_of(s21).get("codeword") == "Yes Brother!", state_of(s21))

os.environ["CLAUDE_PLUGIN_OPTION_LANGUAGE"] = "auto"
cfg = tempfile.mkdtemp(prefix="fm_cfg_")
os.environ["CLAUDE_CONFIG_DIR"] = cfg
for setting, phrase in (("Italiano", "Si Fratello!"), ("japanese", "Yes Brother!")):
    with open(os.path.join(cfg, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"language": setting}, f)
    s21 = new_session()
    turn_on(s21)
    check("auto + settings language %s -> %s" % (setting, phrase), state_of(s21).get("codeword") == phrase,
          state_of(s21))
del os.environ["CLAUDE_CONFIG_DIR"]
shutil.rmtree(cfg, ignore_errors=True)

os.environ["CLAUDE_PLUGIN_OPTION_CODEWORD"] = "Agli ordini!"
s21 = new_session()
turn_on(s21)
check("codeword option overrides default", state_of(s21).get("codeword") == "Agli ordini!", state_of(s21))
del os.environ["CLAUDE_PLUGIN_OPTION_CODEWORD"]
os.environ["CLAUDE_PLUGIN_OPTION_LANGUAGE"] = "italian"

# 22. commands with the plugin prefix (/fazen-memory:<skill>)
s22 = new_session()
run("on_prompt.py", {"session_id": s22, "prompt": "/fazen-memory:fazenmemory"})
check("prefixed /fazenmemory -> on", state_of(s22).get("enabled") is True, state_of(s22))
run("on_prompt.py", {"session_id": s22, "prompt": "/fazen-memory:fmcodeword Agli ordini!"})
check("prefixed /fmcodeword -> phrase", state_of(s22).get("codeword") == "Agli ordini!", state_of(s22))
run("on_prompt.py", {"session_id": s22, "prompt": "/fazen-memory:fmhandoff"})
check("prefixed /fmhandoff -> marked", state_of(s22).get("handoff_requested") is True, state_of(s22))
run("on_prompt.py", {"session_id": s22, "prompt": "/fazen-memory:fazenmemory off"})
check("prefixed /fazenmemory off", not state_of(s22).get("enabled"), state_of(s22))

# 23. one long autonomous turn (seen live in handoff chat #4): a progress note comes first, the final
#     reply starts with the code word, big context -> not a miss
def long_turn(first, last, tokens=335000):
    path = os.path.join(tempfile.gettempdir(), "fm_t_%s.jsonl" % uuid.uuid4().hex)
    rows = [{"type": "user", "message": {"content": "Fazen Memory resume: ..."}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": first}],
                                              "usage": {"input_tokens": BASE}}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": last}],
                                              "usage": {"input_tokens": BASE + tokens}}}]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r) for r in rows) + "\n")
    return path

s23 = new_session()
run("on_prompt.py", {"session_id": s23, "prompt": "/fmcodeword"})
final = "Si Fratello!  Il plugin ora è multilingua."
out = run("on_stop.py", {"session_id": s23, "transcript_path": long_turn("Archivio la chat precedente.", final),
                         "last_assistant_message": final})
check("long turn: progress note first, final reply with code word -> no miss", out == {}, out)
check("long turn: misses not counted", not state_of(s23).get("misses"), state_of(s23))
s23 = new_session()
run("on_prompt.py", {"session_id": s23, "prompt": "/fmcodeword"})
out = run("on_stop.py", {"session_id": s23, "transcript_path": long_turn("Archivio la chat precedente.", "Fatto."),
                         "last_assistant_message": "Fatto."})
check("long turn: code word in neither -> miss counted, warned, no block yet", "decision" not in out
      and "code word" in out.get("systemMessage", "") and state_of(s23).get("misses") == 1, out)

# 24. /fazenmemory status reports what the hooks really saw, and warns when their state was lost
#     (seen live: a cleanup hook emptied the plugin data folder before every Bash call)
def chat(*prompts):
    path = os.path.join(tempfile.gettempdir(), "fm_t_%s.jsonl" % uuid.uuid4().hex)
    rows = []
    for p in prompts:
        rows += [{"type": "user", "message": {"content": p}},
                 {"type": "user", "isMeta": True, "message": {"content": "Base directory for this skill: ..."}},
                 {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
                 {"type": "assistant", "message": {"content": [{"type": "text", "text": "Si Fratello! ok"}]}}]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r) for r in rows) + "\n")
    return path

s24 = new_session()
run("on_prompt.py", {"session_id": s24, "prompt": "/fazenmemory"})
run("on_prompt.py", {"session_id": s24, "prompt": "vai"})
out = run("on_prompt.py", {"session_id": s24, "prompt": "/fazenmemory status",
                           "transcript_path": chat("/fazenmemory", "vai")})
note = note_of(out)
check("status: note with the hooks' data", "status" in note and "on" in note and "Si Fratello!" in note
      and "3" in note, note)
check("status: no warning when nothing was lost", "Warning" not in note, note)
check("status does not change on/off", state_of(s24).get("enabled"), state_of(s24))
out = run("on_prompt.py", {"session_id": s24, "prompt": "/fazenmemory status",
                           "transcript_path": chat("/fazenmemory", "vai", "/fazenmemory status", "/fazenmemory status")})
check("status: current prompt already in the transcript -> no warning", "Warning" not in note_of(out), note_of(out))
s24 = new_session()
out = run("on_prompt.py", {"session_id": s24, "prompt": "/fazenmemory status",
                           "transcript_path": chat("/fazenmemory", "a", "b", "c", "d")})
note = note_of(out)
check("status: state lost -> warning naming the state folder", "Warning" in note and "5" in note
      and STATE in note, note)
check("status in an off chat: says off, stays off", " off" in note and not state_of(s24).get("enabled"), note)

shutil.rmtree(DATA, ignore_errors=True)
print("\nRESULT:", "ALL PASS" if not fails else "FAILED: %s" % fails)
sys.exit(1 if fails else 0)

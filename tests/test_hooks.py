import json, os, subprocess, sys, tempfile, uuid

sys.stdout.reconfigure(encoding="utf-8")  # Windows console is cp1252; hook messages carry emoji

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks")
# Isolated state: the hooks write where an installed plugin would, in a throwaway folder.
DATA = tempfile.mkdtemp(prefix="fm_data_")
os.environ["CLAUDE_PLUGIN_DATA"] = DATA
STATE = os.path.join(DATA, "sessions")
os.makedirs(STATE)
fails = []
# Baseline: an attended chat (test 19 changes it).
os.environ["CLAUDE_CODE_SESSION_ATTENDED"] = "1"


def run(script, payload):
    p = subprocess.run([sys.executable, os.path.join(HOOKS, script)], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, timeout=30)
    assert p.returncode == 0, p.stderr
    out = p.stdout.decode("utf-8").strip()
    return json.loads(out) if out else {}


def transcript(reply, tokens=1000):
    path = os.path.join(tempfile.gettempdir(), "fm_t_%s.jsonl" % uuid.uuid4().hex)
    rows = [
        {"type": "user", "message": {"role": "user", "content": "ciao"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": reply}],
                                          "usage": {"input_tokens": 1, "cache_creation_input_tokens": 0,
                                                    "cache_read_input_tokens": tokens - 1}}},
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

# 2b. miss in a long chat (>= 10 exchanges) -> block + systemMessage, phrase never leaked to Claude
for _ in range(9):
    run("on_prompt.py", {"session_id": s, "prompt": "vai", "transcript_path": t2})
out = run("on_stop.py", {"session_id": s, "transcript_path": t2, "last_assistant_message": "Ecco il codice"})
check("codeword missing -> block", out.get("decision") == "block", out)
check("reason does not leak phrase", "Fratello" not in out.get("reason", ""), out)
check("systemMessage shown", "code word" in out.get("systemMessage", ""), out)

# 3. second miss -> no second block (once per chat), warning only
out = run("on_stop.py", {"session_id": s, "transcript_path": t2, "last_assistant_message": "Ecco il codice"})
check("second miss -> no re-block", "decision" not in out and "systemMessage" in out, out)

# 4. stop_hook_active -> nothing (anti-loop)
out = run("on_stop.py", {"session_id": new_session(), "stop_hook_active": True, "transcript_path": t2})
check("stop_hook_active -> silent", out == {}, out)

# 5. red tokens without codeword -> block
s5 = on_session()
t5 = transcript("risposta", tokens=460000)
out = run("on_stop.py", {"session_id": s5, "transcript_path": t5, "last_assistant_message": "risposta"})
check("red tokens -> block", out.get("decision") == "block" and "460k" in out.get("reason", ""), out)

# 6. below red tokens -> silent
s6 = new_session()
out = run("on_stop.py", {"session_id": s6, "transcript_path": transcript("x", tokens=200000),
                          "last_assistant_message": "x"})
check("below red -> silent", out == {}, out)

# 7. yellow tokens on prompt -> checkpoint note once
s7 = on_session()
t7 = transcript("x", tokens=310000)
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
t9 = transcript("x", tokens=500000)
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
    for _ in range(4000):  # ~20 MB of old history
        f.write(filler + "\n")
    f.write(json.dumps({"type": "user", "message": {"content": "vai"}}) + "\n")
    f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Ecco"}],
                        "usage": {"input_tokens": 470000}}}) + "\n")
s13 = new_session()
run("on_prompt.py", {"session_id": s13, "prompt": "/fmcodeword", "transcript_path": big})
import time as _t
t0 = _t.time()
out = run("on_stop.py", {"session_id": s13, "transcript_path": big, "last_assistant_message": "Ecco"})
dt = _t.time() - t0
check("big transcript: miss + red detected", out.get("decision") == "block" and "470k" in out.get("reason", "")
      and "code word" in out.get("reason", ""), out)
check("big transcript: under 3s (%.2fs)" % dt, dt < 3, dt)
os.remove(big)

# 14. optional: a real transcript passed as argv[1] -> print its context size, compare with get_usage
sys.path.insert(0, HOOKS)
import state  # noqa
if len(sys.argv) > 1:
    n = state.context_tokens(sys.argv[1])
    print("real transcript context tokens:", n)
    check("real transcript tokens > 0", n > 0, n)

def state_of(sid):
    return json.load(open(os.path.join(STATE, sid + ".json"), encoding="utf-8"))


def note_of(out):
    return out.get("hookSpecificOutput", {}).get("additionalContext", "")


# 15. off by default: a new chat without /fazenmemory gets nothing, even past the red marks
s15 = new_session()
t15 = transcript("x", tokens=500000)
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
out = run("on_stop.py", {"session_id": s19, "transcript_path": transcript("Si Fratello! x", tokens=500000),
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

shutil.rmtree(DATA, ignore_errors=True)
print("\nRESULT:", "ALL PASS" if not fails else "FAILED: %s" % fails)
sys.exit(1 if fails else 0)

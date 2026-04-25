# Learnings — Failures, Workarounds & Time Savers

## Purpose
Read this file when hitting a repeated error or unexpected behaviour.
Each bullet is a one-liner under 15 words.
No explanations. Only things that save time in future sessions.

---

## Rules for This File
- One line per learning, under 15 words
- Add immediately when a failure or workaround is found
- Never delete a line — they compound over time
- Group by category as list grows

---

## Supabase
- [ ] Add learnings here as they are discovered

## Auth
- [ ] Add learnings here as they are discovered

## Testing
- [ ] Add learnings here as they are discovered

## Next.js
- [ ] Add learnings here as they are discovered

## Deployment
- [ ] Add learnings here as they are discovered

## General
- pyarrow DLL blocked by Windows App Control — all sklearn/sentence_transformers fail locally
- TRL GRPOConfig import chain: trl→transformers→peft→sklearn→pyarrow (DLL fails on Windows)
- Python 3.13 `try:` shows in traceback frame but except block still executes
- Initialize loop variables (terminated, truncated) BEFORE try/except blocks to avoid NameError
- Greedy `\{.*\}` in re.search captures too much — use balanced-brace walker for JSON extraction
- defender.py LLM sometimes returns multiple JSON objects — "Extra data" JSONDecodeError
- pytest must run from project ROOT, not from viral_script_engine/ subdir (module path issue)
- dry-run patches R2/R5 score methods before env import to avoid pyarrow DLL load
- run_escalation_demo.py must also patch R2/R5 stubs at top before ViralScriptEnv import

## Testing
- Mock R2 CoherenceReward.score and R5 DefenderPreservationReward.score in any env test
- GRPOConfig test: use try/except import, not pytest.importorskip (trl is "installed" but fails)

---

## Example Format (remove when real entries exist)
```
## Supabase
- RLS blocks all queries by default — always add select policy first
- supabase db push fails silently if migration has syntax error
- Foreign key inserts require parent row to exist first

## Auth
- JWT expires after 1hr — always call refreshSession before DB ops
- getSession returns null on hard refresh — use onAuthStateChange instead

## Testing
- Jest mock must be reset between tests or state bleeds across cases
- Supabase client must be mocked at module level not inside test

## Next.js
- useEffect runs twice in strict mode — guard with cleanup function
- API routes do not have access to cookies without explicit parsing
```
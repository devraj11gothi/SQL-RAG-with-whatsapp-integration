# Memory — Progress Log

Living doc. Update at end of every session / completed phase step. Read this first when resuming work — tells you what's done and what's next.

## Current Status
**Phase: 8 (Review Pass) — done. All phases 0-8 complete. v1 build finished.**
Docs complete: PRD.md, architecture.md, rules.md, phases.md, memory.md.
DB: local MySQL installed via brew, `chinook` DB + `chinook_app` user created, Chinook data imported (3503 tracks verified). LMStudio confirmed reachable, `google/gemma-4-e4b` loaded.
Chose local MySQL over Supabase/Postgres when asked mid-build (no code written yet at that point, low switch cost, but stuck with plan per PRD's local-only decision).
Code: `app/config.py`, `app/db.py` (no guard yet — Phase 2), `app/llm_client.py`, `app/schema_context.py` (hardcoded 4-table subset — Phase 4 replaces), `app/pipeline.py` (no retry yet — Phase 3), `prompts/sql_gen_system.txt`, `prompts/answer_gen_system.txt`. Venv at `.venv/`.
Verified: "How many tracks are there?" → correct answer, 0.6s total (well under 15s budget).
Known issue (not blocking): on a join question ("which genre has most tracks"), SQL was correct but answer-gen LLM misread the single-row result and said "not enough info" — small-model reasoning weakness, matches PRD risk #1. Revisit if it persists after full schema (Phase 4) / prompt tuning.

## Key Decisions (locked, from PRD/architecture discovery)
- DB: MySQL, local install (not Docker). Chinook schema from `data/Chinook_MySql.sql`.
- LLM: LMStudio, model `google/gemma-4-e4b`, endpoint `http://192.168.1.253:1234/v1`.
- Query flow: single-shot NL→SQL, 1 retry on SQL error, then NL answer. No agentic multi-step loop (deferred).
- Read-only enforced at app layer only (`sql_guard.py`) — no DB-level read-only user in v1.
- Session memory: in-memory only, per Streamlit session, not persisted across restarts.
- Stack: Python, SQLAlchemy Core, Streamlit UI (single process), `.env` config.
- Build order: vertical slice first (Phase 1), then layer in safety/retry/schema/session/UI/logging.
- Auto row LIMIT cap (default 200) injected if missing.

## Log

### 2026-07-24
- Discovery + doc phase complete. Created PRD.md, architecture.md, rules.md, phases.md, memory.md.
- Phase 0 scaffolding created: `requirements.txt` (PyMySQL chosen as driver), `.env.example`, `setup_db.sh` (installs MySQL via brew, creates `chinook` DB + `chinook_app` user, imports `data/Chinook_MySql.sql`), `.gitignore`.
- Phase 0 + 1 + 2 completed. `app/sql_guard.py` added (sqlparse-based: single-statement check, SELECT/WITH-only, LIMIT injection), wired into `pipeline.py` before `db.execute_readonly`. `pytest.ini` added (`pythonpath = .`) so `tests/` can import `app`. `tests/test_sql_guard.py` — 11 tests, all pass, offline/no DB dependency per rules.md. Re-verified pipeline still answers correctly with guard active.
- Phase 3 done: `db.SQLExecutionError` typed error added, `pipeline.py` refactored with `_generate_sql(question, error=None)` helper + single retry on `UnsafeSQLError`/`SQLExecutionError`, raises `PipelineError` (user-safe message) if retry also fails. `tests/test_pipeline.py` — 2 tests w/ mocked llm_client+db (retry-succeeds, both-fail), all offline. Full suite: 13 tests pass.
- Live-verified retry: real question hit genuine MySQL error (`LIMIT & subquery` unsupported), retry regenerated SQL, succeeded without exception. Confirms retry path works end-to-end, not just mocked.
- Known issue (Phase 4 will fix): hardcoded 4-table schema subset lacks Artist table properly wired for artist-name lookups — caused a wrong-but-non-erroring answer on "what genre does AC/DC make". Not a pipeline bug, a schema-context gap.
- Phase 4 done: `schema_context.py` rewritten to introspect live DB via SQLAlchemy `inspect()` (not regex-parsing the .sql file — more robust), builds full schema text (all 11 tables, columns, FKs) once at process start, cached in `SCHEMA_TEXT`. Replaced Phase 1's hardcoded 4-table subset.
- Verified: previous wrong-answer case ("what genre does AC/DC make") now correct (proper Artist->Album->Track->Genre join). Harder 5-table aggregation ("top 5 artists by total sales") also correct.
- Bug fixed (found during testing, not scope creep): `json.dumps(rows)` crashed on MySQL `Decimal` results (from `SUM`) — fixed with `default=str` in `pipeline.py`.
- Latency watch: 5-table join question took 14s total (right at the 15s budget edge) — flag for Phase 8 QA pass, may need prompt/context trimming if this recurs often.
- Phase 5 done: `app/session.py` — `Session` class holds last 5 turns (question/sql/answer), `context_text()` formats them for the SQL-gen prompt. `pipeline.answer_question()` now takes optional `session` param, prepends context, records turn on success. Existing tests unaffected (session=None default preserves old behavior).
- Live-verified follow-up: "Which country's customers spent the most?" → USA, then "now just show the top 3" correctly reused prior query context and returned top-3 ranked list (USA/Canada/France). Second turn only 1.9s (cheaper — smaller/simpler regenerated query).
- Phase 6 done: `app/main.py` Streamlit chat UI — `st.session_state` holds `Session` + message list, chat input/history, spinner + elapsed-time caption, expandable "Show generated SQL" per answer.
- Bug fixed during build: `streamlit run app/main.py` put `app/` (not project root) on `sys.path`, breaking `from app.pipeline import ...` (`ModuleNotFoundError: No module named 'app'`). Fixed with `sys.path.insert(0, project_root)` at top of `main.py` — permanent fix, no env var needed at launch.
- Browser-verified (via claude-in-chrome) full golden path: asked "How many albums does Iron Maiden have?" → correct (21), 1.1s, SQL expander works. Follow-up "what about Metallica?" → correctly used session context, correct (10 albums), 1.0s.
- To run app: `.venv/bin/streamlit run app/main.py` from project root.
- Phase 7 done: `app/logging_setup.py` — `get_logger()` gives console + rotating file (`logs/app.log`, 1MB x3 backups) handler. `pipeline.py` `print()`s replaced with logger calls (question, SQL, timing, retry warnings). `llm_client.py` wraps `requests` connection failures into typed `LLMConnectionError`. `pipeline.py` catches `LLMConnectionError` around both LLM calls, raises `PipelineError` with friendly message ("Can't reach the LLM server..."). `main.py` already caught `PipelineError` from Phase 6 — friendly messages now flow through automatically, no UI changes needed.
- Live-verified: killed LMStudio reachability (pointed at closed port) → clean `PipelineError` caught, no crash, detailed error logged (console + `logs/app.log`), no secrets in log output. Re-verified normal flow (question + follow-up) still works correctly after changes.
- Note: DB-down and bad-SQL both still map to `db.SQLExecutionError` and get retried once before failing — DB-down will waste one retry cycle with a generic "couldn't generate valid query" message rather than a DB-specific one. Accepted as-is (kept simple per rules.md, no scope creep) — revisit only if it proves confusing in practice.
- Phase 8 done: rules.md checklist run — `black`/`isort` applied (7 files reformatted), 13 tests pass, no hardcoded secrets found (`MYSQL_PASSWORD` only ever referenced via `config.py` env load), no destructive SQL in app code outside guard-rejection tests, `.env` gitignored.
- Manual QA: 10 varied Chinook questions run. Timing mostly 0.6-2.4s, one 5.2s (top-5 ranking question) — all well under 15s budget; the earlier Phase 4 concern about 14s on 5-table joins didn't recur here (simpler queries this round).
- **Real bug found + fixed during QA**: 2 of 10 questions ("longest track", "playlist with most tracks", also affected "employee with most customers") got wrong/hedged answers ("not enough information") despite correct SQL and correct DB rows. Root cause: SQL used the aggregate (COUNT/MAX ordering) only in `ORDER BY`, never selected it — so the answer-gen LLM saw data like `{'Name': 'Music'}` with no visible number to justify "most," and the small model hedged rather than trust the ranking. Fixed with a one-line addition to `prompts/sql_gen_system.txt`: "If ordering or filtering by an aggregate (COUNT, SUM, AVG, etc.), include that aggregate as a named column in the SELECT output, not just in ORDER BY." Re-tested all 3 previously-wrong questions — employee question now fully correct with count (21 customers) and correct answer; playlist/longest-track questions also now answer confidently and correctly.
- Deleted temporary `scripts_qa.py` (was QA scratch tool only, not part of the app).
- **v1 BUILD COMPLETE.** All 8 phases done. App runnable via `.venv/bin/streamlit run app/main.py`. Remaining scope explicitly deferred (see phases.md "Future/Out of Scope"): multi-step agentic loop, DB-level read-only user, persistent sessions, streaming UI, auth/hosting.
- If resuming: nothing blocking. Possible next steps are user-driven — e.g. try more QA questions, decide if any "Future" item should be promoted into scope, or just use the app as-is.

### 2026-07-24 (post-v1 hardening round)
- User asked what question categories should be expected to fail; agent listed 12 (multi-hop reasoning, fuzzy name match, ambiguous columns, >1 retry, row-limit truncation, non-SELECT phrased as question, missing-aggregate-in-SELECT, time-relative questions, subjective/opinion questions, schema-introspection questions, long follow-up chains beyond 5-turn window, prompt injection via question text).
- User tested #1 (multi-hop) manually: "which genre's tracks are bought most by customers in countries where the support rep has been employed >5 years" → got "Rock, 835". Verified: the number is factually correct (confirmed via raw SQL), but the model's SQL silently dropped the "in countries" clause entirely — answered a simpler question than asked, no error, no hedge. Real known failure mode: multi-constraint questions can get partially ignored without any signal to the user. Not fixed (out of scope for a small local model — documented as a known limitation, not a bug).
- Fixed 3 categories per user request, all via `prompts/sql_gen_system.txt` additions + `pipeline.py`/`main.py` changes (no scope creep, no new deps):
  1. **Fuzzy name matching (#2)**: prompt now instructs `LIKE '%value%'` instead of exact `=` for name/title filters. Verified: "iron maden" (typo) now correctly resolves. Known remaining gap: typos that drop special characters (e.g. "acdc" vs stored "AC/DC") still fail — `LIKE` can't bridge that, would need real fuzzy-string matching, not implemented.
  2. **Retry-exhausted transparency (#4)**: `PipelineError` now carries `.sql` (last attempted query). `main.py` shows it in the SQL expander even on failure (previously showed nothing on error). Retry cap itself unchanged (still 1, per original locked PRD/rules.md decision — latency budget takes priority, not touched).
  3. **Subjective questions (#9)**: prompt adds a `NO_QUERY` sentinel — model outputs this literal string when a question has no data-backed answer. `pipeline._generate_sql` detects it, `answer_question` short-circuits with a fixed friendly message, skips DB call and second LLM call entirely (cheap + deterministic, no hallucination risk). Verified: "what genre do you personally like" → correctly triggers `NO_QUERY`. Verified: "what is the best genre" → model chose a data-backed proxy (revenue) instead of refusing — reasonable, not a bug.
- All 13 existing tests still pass unchanged (mocks unaffected by these prompt/error-object changes). No new tests added for `NO_QUERY` path or `LIKE` behavior — both are prompt-driven (non-deterministic LLM output), not suited to unit tests; validated manually instead, consistent with how schema/prompt quality was verified in earlier phases.
- Still-open known failure categories (not touched, from the original list of 12): #1 multi-hop constraint-dropping (confirmed live, not fixable simply), #3 ambiguous column reference, #5 row-limit truncation w/o mention, #6 non-SELECT phrased as question (guard blocks it but UX not tested), #7 aggregate-omission recurrence (mitigated Phase 8, not guaranteed), #8 time-relative questions, #10 schema-introspection questions, #11 >5-turn session context loss, #12 prompt injection via question text.

### 2026-07-24 (fuzzy-match round 2 — LIKE alone insufficient)
- User found LIKE-only fix from round 1 still failed: "what genre does Alanis Morsette make" (typo for "Morissette") → "cannot answer" / empty rows. Root cause: `LIKE '%value%'` requires the typo'd text to be a literal substring of the real value — "Morsette" is NOT a substring of "Morissette" (missing 'i' mid-word breaks contiguous match), so no amount of wildcarding helps this typo shape.
- Fix: added `SOUNDEX(column) = SOUNDEX('value')` (MySQL builtin phonetic match, no new dependency) alongside `LIKE`, in `prompts/sql_gen_system.txt`. Verified via raw SQL that `SOUNDEX('Alanis Morsette') = SOUNDEX('Alanis Morissette')` — confirmed match. Also incidentally fixed the earlier-documented "acdc" vs "AC/DC" gap (`SOUNDEX('ACDC') = SOUNDEX('AC/DC')` — verified).
- First attempt regressed: model sometimes split multi-word names into separate words and compared each word's SOUNDEX against the *whole* column (`SOUNDEX('Alanis') = SOUNDEX(T1.Name)` where Name is the full "Alanis Morissette") — never matches since soundex of one word differs from soundex of the full multi-word string. Confirmed via raw SQL (`SOUNDEX('Alanis')` = 'A452' vs `SOUNDEX('Alanis Morissette')` = 'A4525623').
- Tightened prompt further: explicit instruction to match using the FULL name as one string, never split into separate words. Re-tested 3x for "Alanis Morsette" and 2x for "iron maden" — all runs now correct (Rock / 21 albums respectively). Small model behavior is still non-deterministic per-call (SQL text varies each run), but outcome now consistently correct across repeats for these two cases.
- All 13 tests still pass (no test coverage added for SOUNDEX behavior — same rationale as round 1: prompt-driven LLM output isn't suited to deterministic unit tests, validated manually via repeated runs instead).
- Residual known limitation: fuzzy matching (LIKE + SOUNDEX) is prompt-driven, so correctness is probabilistic, not guaranteed, on a 4B local model. Encourage continued spot-testing rather than treating this as fully solved.

### 2026-07-24 (temperature fix — real inconsistency root cause)
- User reported same question ("Alanis Morsette") gave different results run to run — sometimes correct, sometimes "cannot answer." Root cause: `llm_client.chat()` never set a `temperature` param, so LMStudio used its default (~0.7-0.8), making SQL generation genuinely non-deterministic per call — not just "small model weirdness" as previously assumed, but a real missing config.
- Fix: added `temperature: float = 0.1` param to `llm_client.chat()`, sent in the request payload. Low value chosen since SQL generation needs precision/determinism, not creativity.
- Verified: ran "what genre does Alanis Morsette make" 5x in a row post-fix — identical correct answer ("Rock") every time. All 13 tests still pass.
- This likely also stabilizes the earlier-documented non-determinism notes (round 1 and round 2 fuzzy-match testing) — worth re-spot-checking "iron maden", "acdc" etc. if time permits, though not re-verified in this round.

## Open Items / Watch
- Latency risk: 15s budget across 2 LLM calls (3 on retry) on local small model — watch actual timings from Phase 1 onward, note here if budget needs revisiting.
- LMStudio LAN IP (`192.168.1.253`) may change if host device's IP changes — update `.env` if connection fails.

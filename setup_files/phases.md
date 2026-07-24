# Phases — Chat with SQL

Build order: vertical slice first — get thin end-to-end path working, then layer in safety/robustness/polish. One commit per completed step (per rules.md).

## Phase 0 — Environment Setup
- Create `requirements.txt` (streamlit, sqlalchemy, pymysql/mysql-connector-python, python-dotenv, requests, sqlparse, pytest, black, isort).
- Write `setup_db.sh` (or `.md` instructions) + `.env.example`: create MySQL database, create user/grants, import `data/Chinook_MySql.sql`. **User runs this manually** (per decision — touches local MySQL install).
- Verify: user confirms Chinook DB queryable locally (`mysql -u ... -e "SELECT COUNT(*) FROM Track;"`), and LMStudio server reachable at `192.168.1.253:1234` with `google/gemma-4-e4b` loaded.
- Exit criteria: DB up, LMStudio reachable, `.env` filled in.

## Phase 1 — Vertical Slice (thin end-to-end path)
- `config.py`: load `.env`.
- `db.py`: minimal `execute_readonly(sql)` — no guard yet, just connect + run + return rows.
- `llm_client.py`: minimal `chat(messages)` hitting LMStudio `/v1/chat/completions`.
- `schema_context.py`: hardcode/paste a small subset of schema text (a few tables) to start.
- `pipeline.py`: single hardcoded question (e.g. "How many tracks are there?") → LLM generates SQL → execute → LLM answers. Run as a script (`python -m app.pipeline`), no UI yet.
- Exit criteria: one real question answered correctly end-to-end via terminal, timed (<15s logged).

## Phase 2 — Safety Layer
- `sql_guard.py`: SELECT-only validation, stacked-statement rejection, LIMIT injection (`MAX_ROW_LIMIT`).
- Wire into `pipeline.py` before every `db.execute_readonly` call.
- Unit tests (`pytest`) for guard: valid SELECT passes, DROP/DELETE/UPDATE/INSERT/ALTER/TRUNCATE rejected, stacked `;` statements rejected, LIMIT injected only when missing.
- Exit criteria: guard tests green, pipeline still answers Phase 1 question correctly through the guard.

## Phase 3 — Retry Logic
- `pipeline.py`: on `SQLExecutionError`, feed error text back to LLM, regenerate SQL once, re-run through guard + execute. If retry also fails, return clean user-facing error (no crash).
- Unit tests (mocked LLM/DB): first-attempt failure → retry succeeds; both fail → clean error surfaced.
- Exit criteria: retry tests green; manually verify with a deliberately ambiguous question that triggers a first-attempt SQL error.

## Phase 4 — Full Schema Context
- `schema_context.py`: extract full Chinook schema (all tables/columns/FKs) from `data/Chinook_MySql.sql` (or DB introspection once), format compactly, cache for process lifetime.
- Replace hardcoded subset from Phase 1 with full schema in prompt.
- Exit criteria: questions spanning multiple/joined tables (e.g. "top 5 artists by total sales") answered correctly.

## Phase 5 — Session Memory
- `session.py`: conversation history store (list of turns).
- `pipeline.py`: include last N turns in SQL-gen prompt for follow-up context.
- Exit criteria: manual test — ask a question, then a follow-up referencing it ("now filter by 2013") and get a contextually correct answer.

## Phase 6 — Web UI
- `main.py`: Streamlit chat interface — input box, message history display, spinner/timing, expandable "show generated SQL" per answer.
- Wire to `pipeline.py` + `session.py` (`st.session_state`).
- Exit criteria: full chat flow usable in browser, matches all prior phase behavior.

## Phase 7 — Logging & Error Polish
- `logging` setup: console + rotating file (`logs/`), log question/SQL/timing per stage, no secrets.
- Friendly error messages surfaced in UI for: LMStudio unreachable, DB unreachable, retry exhausted.
- Exit criteria: kill LMStudio mid-test → clean error in UI, not a crash. Same for DB down.

## Phase 8 — Review Pass
- Run rules.md checklist: black/isort clean, tests pass, no secrets in diff, no destructive SQL anywhere, matches architecture.md.
- Manual QA pass: ~10 varied Chinook questions (simple lookup, aggregation, join, follow-up), record actual latency vs 15s target.
- Exit criteria: checklist complete, QA results logged in memory.md.

## Future / Out of Scope (not this build)
- Multi-step agentic query loop (LLM autonomously issuing N queries).
- DB-level read-only MySQL user (defense-in-depth beyond app-level guard).
- Persistent session storage across restarts.
- Streaming token-by-token answers.
- Auth / multi-user / hosted deployment.

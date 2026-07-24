# Architecture — Chat with SQL

## 1. Stack
- Language: Python 3.11+
- Web/chat UI: Streamlit (single process, in-app)
- DB access: SQLAlchemy Core (connection pool, parameterized/safe execution)
- DB: MySQL (local install), Chinook schema/data from `data/Chinook_MySql.sql`
- LLM: LMStudio, OpenAI-compatible API at `http://192.168.1.253:1234/v1`, model `google/gemma-4-e4b`
- Config: `.env` (python-dotenv) + `.env.example` checked in
- Logging: stdlib `logging`, console + rotating file

## 2. Project Layout
```
SQL_RAG/
├── data/
│   └── Chinook_MySql.sql          # schema + seed data, imported once into MySQL
├── app/
│   ├── main.py                    # Streamlit entrypoint (chat UI)
│   ├── config.py                  # loads .env: DB creds, LMStudio endpoint/model
│   ├── db.py                      # SQLAlchemy engine, connection, safe execute()
│   ├── schema_context.py          # extracts/caches static schema text for prompts
│   ├── llm_client.py              # thin client for LMStudio /v1/chat/completions
│   ├── sql_guard.py                # SELECT-only validation, LIMIT injection
│   ├── pipeline.py                 # orchestrates: NL->SQL->execute->retry->NL answer
│   └── session.py                  # in-memory session/conversation history
├── prompts/
│   ├── sql_gen_system.txt          # system prompt: schema + rules for NL->SQL
│   └── answer_gen_system.txt       # system prompt: result data -> NL answer
├── logs/                           # rotating log files (gitignored)
├── .env.example
├── .env                            # gitignored
├── requirements.txt
├── PRD.md / architecture.md / rules.md / phases.md / memory.md
```

## 3. Component Responsibilities

### `config.py`
Loads: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`, `LMSTUDIO_BASE_URL` (`http://192.168.1.253:1234/v1`), `LMSTUDIO_MODEL` (`google/gemma-4-e4b`), `MAX_ROW_LIMIT` (default 200), `LLM_TIMEOUT_S`.

### `db.py`
- SQLAlchemy `Engine` w/ connection pool (pool_size small, e.g. 5 — single user).
- `execute_readonly(sql: str) -> list[dict]`: runs query, returns rows as dicts. Sets a statement timeout where supported. Wraps errors into typed `SQLExecutionError` with driver message (fed back to LLM on retry).

### `schema_context.py`
- On startup, either reads `CREATE TABLE` statements out of `data/Chinook_MySql.sql` directly (regex/parse), or introspects DB once and caches in memory/file.
- Produces compact schema text (table names, columns, types, FKs) — kept small to save LLM context budget.
- Cached for process lifetime (static per PRD decision).

### `sql_guard.py`
- `validate_select_only(sql: str)`: parses/checks statement type (e.g. via `sqlparse` or simple regex on first keyword after stripping comments/whitespace). Rejects anything not starting with `SELECT`/`WITH ... SELECT`. Blocks multiple statements (`;` splitting) to prevent stacked queries.
- `inject_limit(sql: str, max_rows: int) -> str`: appends `LIMIT max_rows` if no `LIMIT` clause present.

### `llm_client.py`
- `chat(messages, system_prompt) -> str`: POSTs to LMStudio `/v1/chat/completions`, OpenAI-compatible payload, model=`google/gemma-4-e4b`. Configurable timeout (part of 15s budget). Raises typed error on timeout/connection failure (LMStudio host unreachable).

### `pipeline.py` — core orchestration
```
def answer_question(question, session_history):
    sql = llm_generate_sql(question, schema_context, session_history)
    guard.validate_select_only(sql)
    sql = guard.inject_limit(sql)
    try:
        rows = db.execute_readonly(sql)
    except SQLExecutionError as e:
        sql_retry = llm_generate_sql(question, schema_context, session_history, error=e)
        guard.validate_select_only(sql_retry)
        sql_retry = guard.inject_limit(sql_retry)
        rows = db.execute_readonly(sql_retry)   # let this raise if still fails
    answer = llm_generate_answer(question, rows)
    return answer, sql, rows
```
- Single retry only, per PRD. If retry also fails, surface friendly error to user ("couldn't answer that, try rephrasing") — do not crash UI.
- Each stage timed and logged.

### `session.py`
- In-memory list per Streamlit session (`st.session_state`): `[{role, content, sql?, timestamp}]`.
- Last N turns (e.g. 5) passed into `llm_generate_sql` prompt for follow-up context. No persistence across app restarts (v1 scope — local single-session tool).

### `main.py` (Streamlit)
- Chat input → `pipeline.answer_question()` → display answer, optionally show generated SQL in expandable debug section.
- Shows spinner / elapsed time.

## 4. Prompt Design
- **SQL-gen system prompt**: schema text + rules ("only SELECT", "MySQL dialect", "use exact table/column names", output SQL only, no markdown fences ideally — parse defensively either way).
- **Answer-gen system prompt**: given question + result rows (JSON/table, truncated if large) → concise NL answer. Instruct: if rows empty, say so plainly; don't hallucinate beyond given data.

## 5. Error Handling
- LMStudio unreachable/timeout → user-facing error, logged with endpoint.
- Invalid SQL after retry → user-facing "couldn't generate valid query" message.
- Non-SELECT generated → blocked before execution, treated as generation failure, triggers retry path.
- DB connection failure → user-facing error, logged.

## 6. Latency Budget (target <15s)
- LLM call 1 (NL→SQL): ~5-7s (local small model)
- DB execute: <1s (Chinook is small, LIMIT capped)
- LLM call 2 (result→answer): ~5-7s
- Retry path (if triggered) adds one more SQL-gen round — accept occasional overshoot on retry case, documented as known tradeoff.

## 7. Security
- Read-only enforced at app layer (`sql_guard.py`) — per PRD decision (app-level only, not DB-level user, for v1 simplicity).
- No stacked/multi-statement execution allowed.
- `.env` gitignored, never logged.

## 8. Future (out of v1 scope, noted for phases.md)
- Multi-step agentic query loop.
- DB-level read-only MySQL user as defense-in-depth.
- Persistent session storage.
- Streaming answer tokens in UI.

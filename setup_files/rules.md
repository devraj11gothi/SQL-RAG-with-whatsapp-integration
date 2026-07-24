# Rules — Chat with SQL

Binding rules for anyone (human or AI agent) building/modifying this project. Follow architecture.md for structure, phases.md for sequencing.

## 1. Code Style
- Python 3.11+, type hints on all function signatures.
- Format with `black`, imports sorted with `isort`. Run before every commit.
- No commented-out dead code. No TODO left unexplained (link to phases.md item if deferred).
- Docstrings only where behavior is non-obvious (e.g. retry logic, guard regex) — not on every function.

## 2. Testing
- `pytest` required for:
  - `sql_guard.py` — SELECT-only validation (reject DROP/DELETE/UPDATE/INSERT/ALTER/TRUNCATE, reject stacked statements, accept valid SELECT/WITH), LIMIT injection logic.
  - `pipeline.py` — retry-once behavior (mock LLM + DB: first SQL fails, retry succeeds; retry also fails → clean error, no crash).
- No UI tests, no integration tests against live LMStudio/MySQL required for v1.
- Tests must run offline (mock LLM client and DB calls) — no network/DB dependency in test suite.

## 3. Git Workflow
- One commit per completed phase step (see phases.md). No giant multi-feature dumps.
- Commit message: what + why, no filler.
- Never commit: `.env`, `logs/`, `__pycache__`, any file containing credentials or the actual LMStudio LAN IP if it changes to something sensitive.
- `.env.example` always kept in sync with `config.py`'s expected vars (names only, no real values).

## 4. Hard Constraints (never violate)
1. **Never commit secrets.** `.env` gitignored from commit 1. Never print/log `MYSQL_PASSWORD` or other credential values, even in debug logging.
2. **Never run destructive SQL against the real DB**, including during dev/testing/setup. Schema/data setup = fresh import of `data/Chinook_MySql.sql` only. No `DROP`/`DELETE`/`TRUNCATE`/`UPDATE`/`INSERT` scripts against the working DB, ever — this includes "helper" reset scripts.
3. **No scope creep.** Do not build multi-step agentic loop, auth, multi-tenant, hosting, streaming UI, or anything not in current phases.md step. If it seems needed, flag it and add to phases.md — don't silently build it.
4. **Read-only enforcement is non-negotiable.** `sql_guard.py` check runs before every DB execution, no bypass path, no "trusted" query shortcut.
5. **No raw string-interpolated SQL execution** outside the LLM-generated query path — all app-internal DB access (if any) uses parameterized SQLAlchemy calls.

## 5. LLM Interaction Rules
- System prompts (`prompts/*.txt`) are the single source of truth for LLM instructions — don't duplicate/hardcode prompt text elsewhere in code.
- Every LLM call must have a timeout (`LLM_TIMEOUT_S` from config) — no unbounded waits.
- Log: question, generated SQL (both attempts if retried), execution time per stage. Never log DB credentials or full `.env` contents.

## 6. Error Handling
- Every user-facing failure path returns a plain-language message — never raw stack traces or driver errors to the Streamlit UI.
- Full exception detail goes to logs only.

## 7. Review Checklist (before marking a phase done)
- [ ] Code formatted (black/isort clean)
- [ ] Relevant tests pass (`pytest`)
- [ ] No secrets in diff (`git diff` reviewed)
- [ ] No destructive SQL introduced
- [ ] Matches architecture.md component boundaries
- [ ] Matches current phases.md scope, nothing extra added

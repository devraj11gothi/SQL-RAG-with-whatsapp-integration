# PRD — Chat with SQL (LLM Agent)

## 1. Problem
User wants natural-language chat interface over Chinook MySQL DB. No SQL knowledge needed to query data.

## 2. Goal
Question (NL) → LLM generates SQL → execute on MySQL → LLM turns result into NL answer. Session-aware (follow-ups work). Response target: <15s.

## 3. Scope (v1)
- Single DB: Chinook (`data/Chinook_MySql.sql`), MySQL.
- Single-shot query flow: generate SQL → execute → on SQL error, retry once with error fed back to LLM → generate answer. No open-ended multi-step agent loop (deferred, see Non-Goals).
- Read-only enforced: only `SELECT` allowed. Reject/strip any DDL/DML (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, etc.) at app layer.
- Session memory: conversation history kept per session, used as context for follow-up questions (e.g. "now filter by 2023").
- Simple web chat UI (Streamlit or Gradio).
- Local-only, single user. Runs on Mac, calls LMStudio over LAN.

## 4. Non-Goals (v1)
- No multi-step/agentic query loop (LLM autonomously running N queries) — future scope, mentioned in phases.md as a later phase.
- No multi-tenant / auth / hosted deployment.
- No write operations.
- No support for DBs other than Chinook/MySQL.
- No streaming token-by-token UI (nice-to-have, not required).

## 5. Users
Just the one dev (you), local exploratory tool.

## 6. Flow
```
User question (NL)
   ↓
[LLM Call 1: NL → SQL]  (context: schema + conversation history)
   ↓
Execute SQL on MySQL (read-only guard)
   ↓ (on SQL error)
[LLM Call 1-retry: NL + error → SQL]   (max 1 retry)
   ↓
Query result (rows)
   ↓
[LLM Call 2: question + result data → NL answer]
   ↓
Answer shown in chat UI, turn appended to session history
```

## 7. Model / Infra
- LLM: `google/gemma-4-e4b`, hosted via LMStudio.
- Endpoint: `192.168.1.253:1234` (LMStudio OpenAI-compatible API, `/v1/chat/completions`).
- DB: MySQL, schema/data from `data/Chinook_MySql.sql`.

## 8. Success Criteria
- Correct answers for common Chinook questions (top artists, sales by country, customer spend, track counts, etc.).
- p50 response time <15s on local LMStudio model.
- No write/destructive SQL ever reaches DB.
- Follow-up questions resolve correctly using session context.

## 9. Risks
- Small local model (gemma-4-e4b) may generate invalid/wrong SQL more often than hosted large models → mitigated by 1 retry + schema context + read-only guard.
- 15s budget tight for 2 LLM calls + DB roundtrip on local hardware → may need prompt/context trimming.
- LAN dependency: LMStudio host must stay reachable at fixed IP.

## 10. Open Questions
None blocking — resolved via discovery. Revisit multi-step agent scope after v1 validated.

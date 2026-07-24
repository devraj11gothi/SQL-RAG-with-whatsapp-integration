# Chat with SQL

Ask questions in plain English about the Chinook music store database and get answers, powered by an LLM (local via LMStudio, or a cloud API like Gemini).

## How it works

```
Your question → LLM writes SQL → SQL runs on MySQL → LLM turns the result into a plain-language answer
```

## Prerequisites

- Python 3.11+
- MySQL (installed locally, or accessible over a network)
- One of:
  - **LMStudio** running a model, reachable over the network, OR
  - A **Gemini API key** (or any other OpenAI-compatible LLM API)

## 1. Get the code

```bash
git clone <repo-url>   # or copy the project folder
cd SQL_RAG
```

## 2. Set up Python environment

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 3. Set up the database

The Chinook schema + data lives in `data/Chinook_MySql.sql`.

**Option A — automated (Mac, Homebrew):**
```bash
./setup_db.sh
```
This installs MySQL via Homebrew (if not already installed), creates a `chinook` database and a `chinook_app` user, and imports the data. Edit `DB_USER`/`DB_PASSWORD` at the top of the script first if you want different values.

**Option B — manual (any OS):**
```bash
mysql -u root -e "CREATE DATABASE chinook; CREATE USER 'chinook_app'@'localhost' IDENTIFIED BY 'yourpassword'; GRANT ALL ON chinook.* TO 'chinook_app'@'localhost';"
mysql -u root chinook < data/Chinook_MySql.sql
```

## 4. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env` and fill in:

- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB` — match whatever you set up in step 3.
- `LLM_PROVIDER` — `lmstudio` or `gemini` (see step 5).

**Never commit `.env`** — it's already gitignored. It holds real credentials/API keys.

## 5. Configure your LLM

### Option A — LMStudio (local, free, private)

1. Install [LMStudio](https://lmstudio.ai), download a model (this project was built/tested against `google/gemma-4-e4b` and a 12B variant).
2. Load the model, start the local server (LMStudio's "Developer" / server tab).
3. If running the app from a different device than LMStudio, enable "Serve on Local Network" in LMStudio settings and note the LAN IP it shows.
4. In `.env`:
   ```
   LLM_PROVIDER=lmstudio
   LMSTUDIO_BASE_URL=http://<lmstudio-host-ip>:1234/v1
   LMSTUDIO_MODEL=<exact model id from LMStudio>
   ```
   Get the exact model id with: `curl http://<host>:1234/v1/models`

### Option B — Gemini API (cloud, needs API key)

1. Get an API key from [Google AI Studio](https://aistudio.google.com/apikey).
2. In `.env`:
   ```
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=<your key>
   GEMINI_MODEL=gemini-2.5-flash
   ```

You can switch providers anytime by changing `LLM_PROVIDER` in `.env` and restarting the app — no code changes needed.

## 6. Run the app

```bash
.venv/bin/streamlit run app/main.py
```

Opens a chat UI in your browser. Ask questions like:
- "How many tracks are there?"
- "Which country's customers spent the most?"
- "Top 5 artists by total sales"

Each answer has an expandable "Show generated SQL" section so you can see exactly what query ran.

## 7. Run it from the command line (no UI)

Useful for quick testing:
```bash
.venv/bin/python -c "
from app.pipeline import answer_question
answer, sql, rows = answer_question('How many tracks are there?')
print(answer)
"
```

## 8. Run the tests

```bash
.venv/bin/pytest tests/ -v
```
Tests are offline (mocked LLM/DB calls) — no live LMStudio/MySQL connection needed to run them.

## Project structure

```
app/
  main.py            Streamlit chat UI
  pipeline.py         Core orchestration: question -> SQL -> execute -> answer
  llm_client.py        Talks to LMStudio or Gemini (OpenAI-compatible API)
  db.py                MySQL connection + query execution
  sql_guard.py         Blocks anything except SELECT queries, caps row count
  schema_context.py    Builds the DB schema description sent to the LLM
  session.py           Conversation history for follow-up questions
  config.py            Loads .env
  logging_setup.py     Console + rotating file logging
prompts/               System prompts for the two LLM calls
tests/                 pytest suite (guard + retry logic)
data/                  Chinook_MySql.sql (schema + seed data)
setup_db.sh             DB setup script (Mac/Homebrew)
questions.md            Sample test questions with verified ground-truth answers
setup_files/            Original planning docs (PRD, architecture, rules, phases, memory)
```

## Known limitations

- Small/local LLMs occasionally get complex multi-condition questions partially wrong (e.g. silently drop one filter) without any error — always sanity-check answers to important questions, especially multi-table ones.
- Name/artist matching tolerates typos and case differences (via `LIKE` + `SOUNDEX`) but isn't perfect, especially for names with unusual punctuation.
- Read-only by design: the app can never modify or delete data, only `SELECT` queries are allowed.
- Session memory (follow-up questions) only remembers the last 5 turns and resets when the app restarts.

## Troubleshooting

- **"Can't reach the LLM server"** — check LMStudio/Gemini is running and `.env` has the right URL/key.
- **"Can't reach the database"** — check MySQL is running (`brew services list` on Mac) and `.env` credentials are correct.
- **Answers seem wrong** — check the "Show generated SQL" expander; if the SQL itself looks wrong, try rephrasing the question or check `questions.md` for known-tricky cases.

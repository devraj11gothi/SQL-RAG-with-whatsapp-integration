import json
import re
import time
from pathlib import Path

from app import config, db, llm_client, sql_guard
from app.logging_setup import get_logger
from app.schema_context import SCHEMA_TEXT
from app.session import Session

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
SQL_GEN_PROMPT = (
    (PROMPTS_DIR / "sql_gen_system.txt").read_text().format(schema=SCHEMA_TEXT)
)
ANSWER_GEN_PROMPT = (PROMPTS_DIR / "answer_gen_system.txt").read_text()

log = get_logger(__name__)


NO_QUERY = "NO_QUERY"


class PipelineError(Exception):
    """Raised on any user-facing pipeline failure (bad query, LLM/DB unreachable). Safe to show to the user."""

    def __init__(self, message: str, sql: str | None = None):
        super().__init__(message)
        self.sql = sql


def _strip_fences(sql: str) -> str:
    return re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql.strip(), flags=re.IGNORECASE)


def _generate_sql(question: str, context: str, error: str | None = None) -> str:
    user_prompt = f"{context}Question: {question}"
    if error:
        user_prompt += (
            f"\n\nThe previous query failed with error: {error}\nFix the query."
        )
    sql = _strip_fences(llm_client.chat(SQL_GEN_PROMPT, user_prompt))
    if sql.strip().upper() == NO_QUERY:
        return NO_QUERY
    sql_guard.validate_select_only(sql)
    return sql_guard.inject_limit(sql, config.MAX_ROW_LIMIT)


def answer_question(
    question: str, session: Session | None = None
) -> tuple[str, str, list[dict]]:
    t0 = time.time()
    log.info("question: %s", question)
    context = session.context_text() if session else ""
    try:
        try:
            sql = _generate_sql(question, context)
            if sql == NO_QUERY:
                answer = "That's not something I can answer from the database data."
                if session:
                    session.add_turn(question, sql, answer)
                return answer, sql, []
            rows = db.execute_readonly(sql)
        except (sql_guard.UnsafeSQLError, db.SQLExecutionError) as e:
            log.warning(
                "[%.1fs] first attempt failed (%s), retrying", time.time() - t0, e
            )
            try:
                sql = _generate_sql(question, context, error=str(e))
                rows = db.execute_readonly(sql)
            except (sql_guard.UnsafeSQLError, db.SQLExecutionError) as e2:
                raise PipelineError(
                    "Couldn't generate a valid query for that question. Try rephrasing.",
                    sql=sql,
                ) from e2
    except llm_client.LLMConnectionError as e:
        log.error("LLM unreachable: %s", e)
        raise PipelineError(
            "Can't reach the LLM server. Check LMStudio is running and reachable."
        ) from e

    log.info("[%.1fs] SQL: %s, rows: %d", time.time() - t0, sql, len(rows))

    try:
        answer = llm_client.chat(
            ANSWER_GEN_PROMPT,
            f"Question: {question}\nData: {json.dumps(rows, default=str)}",
        )
    except llm_client.LLMConnectionError as e:
        log.error("LLM unreachable: %s", e)
        raise PipelineError(
            "Can't reach the LLM server. Check LMStudio is running and reachable."
        ) from e
    log.info("[%.1fs] answer generated", time.time() - t0)

    if session:
        session.add_turn(question, sql, answer)

    return answer, sql, rows


if __name__ == "__main__":
    session = Session()
    for question in [
        "Which country's customers spent the most?",
        "now just show the top 3",
    ]:
        try:
            answer, sql, rows = answer_question(question, session)
            print(f"\nQ: {question}\nSQL: {sql}\nA: {answer}")
        except PipelineError as e:
            print(f"\nQ: {question}\nError: {e}\nLast SQL tried: {e.sql}")

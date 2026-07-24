import re

import sqlparse


class UnsafeSQLError(ValueError):
    pass


def validate_select_only(sql: str) -> None:
    statements = [s for s in sqlparse.parse(sql) if s.token_first(skip_cm=True)]
    if len(statements) != 1:
        raise UnsafeSQLError(f"expected exactly one statement, got {len(statements)}")

    first_token = statements[0].token_first(skip_cm=True)
    keyword = first_token.value.upper()
    if keyword not in ("SELECT", "WITH"):
        raise UnsafeSQLError(f"only SELECT statements allowed, got: {keyword}")


def inject_limit(sql: str, max_rows: int) -> str:
    sql = sql.rstrip().rstrip(";")
    if re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        return sql
    return f"{sql} LIMIT {max_rows}"

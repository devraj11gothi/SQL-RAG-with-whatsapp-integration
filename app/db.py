from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app import config

_engine = create_engine(
    f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}"
    f"@{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DB}"
)


class SQLExecutionError(Exception):
    pass


def execute_readonly(sql: str) -> list[dict]:
    try:
        with _engine.connect() as conn:
            result = conn.execute(text(sql))
            return [dict(row._mapping) for row in result]
    except SQLAlchemyError as e:
        raise SQLExecutionError(str(e.orig) if hasattr(e, "orig") else str(e)) from e

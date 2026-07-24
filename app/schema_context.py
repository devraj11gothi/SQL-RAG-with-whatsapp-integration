from sqlalchemy import inspect

from app.db import _engine


def _build_schema_text() -> str:
    insp = inspect(_engine)
    lines = []
    for table in insp.get_table_names():
        cols = ", ".join(c["name"] for c in insp.get_columns(table))
        lines.append(f"Table {table}({cols})")
        for fk in insp.get_foreign_keys(table):
            local = ", ".join(fk["constrained_columns"])
            ref_cols = ", ".join(fk["referred_columns"])
            lines.append(f"  FK: {table}.{local} -> {fk['referred_table']}.{ref_cols}")
    return "\n".join(lines)


SCHEMA_TEXT = (
    _build_schema_text()
)  # built once per process, per architecture.md decision

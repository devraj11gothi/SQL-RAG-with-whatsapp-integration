import pytest

from app.sql_guard import UnsafeSQLError, inject_limit, validate_select_only


def test_accepts_select():
    validate_select_only("SELECT * FROM Track")


def test_accepts_with_cte():
    validate_select_only("WITH t AS (SELECT * FROM Track) SELECT * FROM t")


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE Track",
        "DELETE FROM Track",
        "UPDATE Track SET Name='x'",
        "INSERT INTO Track (Name) VALUES ('x')",
        "ALTER TABLE Track ADD COLUMN x INT",
        "TRUNCATE TABLE Track",
    ],
)
def test_rejects_non_select(sql):
    with pytest.raises(UnsafeSQLError):
        validate_select_only(sql)


def test_rejects_stacked_statements():
    with pytest.raises(UnsafeSQLError):
        validate_select_only("SELECT * FROM Track; DROP TABLE Track;")


def test_injects_limit_when_missing():
    assert inject_limit("SELECT * FROM Track", 200) == "SELECT * FROM Track LIMIT 200"


def test_does_not_inject_limit_when_present():
    sql = "SELECT * FROM Track LIMIT 10"
    assert inject_limit(sql, 200) == sql

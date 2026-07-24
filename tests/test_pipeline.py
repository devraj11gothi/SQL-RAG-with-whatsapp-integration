from unittest.mock import patch

import pytest

from app import db
from app.pipeline import PipelineError, answer_question


@patch("app.pipeline.db.execute_readonly")
@patch("app.pipeline.llm_client.chat")
def test_retries_once_after_sql_error_then_succeeds(mock_chat, mock_execute):
    mock_chat.side_effect = [
        "SELECT bad_column FROM Track",  # attempt 1
        "SELECT COUNT(*) FROM Track",  # retry
        "There are some tracks.",  # answer
    ]
    mock_execute.side_effect = [
        db.SQLExecutionError("unknown column bad_column"),
        [{"COUNT(*)": 3503}],
    ]

    answer, sql, rows = answer_question("how many tracks?")

    assert sql == "SELECT COUNT(*) FROM Track LIMIT 200"
    assert rows == [{"COUNT(*)": 3503}]
    assert answer == "There are some tracks."
    assert mock_chat.call_count == 3
    assert mock_execute.call_count == 2


@patch("app.pipeline.db.execute_readonly")
@patch("app.pipeline.llm_client.chat")
def test_raises_clean_error_when_retry_also_fails(mock_chat, mock_execute):
    mock_chat.side_effect = [
        "SELECT bad_column FROM Track",
        "SELECT also_bad FROM Track",
    ]
    mock_execute.side_effect = [
        db.SQLExecutionError("unknown column bad_column"),
        db.SQLExecutionError("unknown column also_bad"),
    ]

    with pytest.raises(PipelineError):
        answer_question("how many tracks?")

    assert mock_chat.call_count == 2
    assert mock_execute.call_count == 2

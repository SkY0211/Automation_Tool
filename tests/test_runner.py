from unittest.mock import MagicMock, patch

import pytest

from backend.cat_a_tool.runner import start_cat_a_test


# --------------------------------------------------
# FIXTURE: Minimal valid config
# --------------------------------------------------

@pytest.fixture
def valid_config():
    return {
        "test_type": "short",
        "iterations": 2,
        "call_duration": 5,     # minutes → should convert to seconds
        "call_delay": 1,
        "mt_number": "1234567890",
        "mo_serial": "MO123",
        "mt_serial": "MT123",
    }


# --------------------------------------------------
# TEST: Call duration conversion (minutes → seconds)
# --------------------------------------------------

@patch("backend.cat_a_tool.runner.threading.Thread")
@patch("backend.cat_a_tool.runner.CallTester")
@patch("backend.cat_a_tool.runner.CustomLogger")
def test_call_duration_converted_to_seconds(
    mock_logger,
    mock_calltester,
    mock_thread,
    valid_config
):
    start_cat_a_test(valid_config)

    # Extract CallTester constructor args
    _, kwargs = mock_calltester.call_args

    assert kwargs["call_duration"] == 300   # 5 * 60
    assert kwargs["iterations"] == 2
    assert kwargs["call_delay"] == 1


# --------------------------------------------------
# TEST: Thread started with correct target
# --------------------------------------------------

@patch("backend.cat_a_tool.runner.threading.Thread")
@patch("backend.cat_a_tool.runner.CallTester")
@patch("backend.cat_a_tool.runner.CustomLogger")
def test_thread_started_for_run_test(
    mock_logger,
    mock_calltester,
    mock_thread,
    valid_config
):
    instance = mock_calltester.return_value

    start_cat_a_test(valid_config)

    mock_thread.assert_called_once()
    thread_kwargs = mock_thread.call_args.kwargs

    assert thread_kwargs["target"] == instance.run_test
    assert thread_kwargs["daemon"] is True


# --------------------------------------------------
# TEST: Graceful failure handling
# --------------------------------------------------

@patch("backend.cat_a_tool.runner.CustomLogger")
@patch("backend.cat_a_tool.runner.CallTester", side_effect=Exception("Boom"))
def test_runner_handles_exception_gracefully(
    mock_calltester,
    mock_logger,
    valid_config
):
    start_cat_a_test(valid_config)

    logger_instance = mock_logger.return_value
    logger_instance.log.assert_any_call("CAT-A RUNNER ERROR: Boom")

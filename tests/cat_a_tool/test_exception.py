import sys
import pytest

from backend.cat_a_tool.exception import error_message_detail, CallException


# --------------------------------------------------
# Test: error_message_detail WITH exc_info
# --------------------------------------------------

def test_error_message_detail_with_exc_info():
    try:
        raise ValueError("Something went wrong")
    except ValueError as e:
        message = error_message_detail(e, sys)

    assert "Error in file" in message
    assert "line number" in message
    assert "Something went wrong" in message


# --------------------------------------------------
# Test: error_message_detail WITHOUT exc_info
# --------------------------------------------------

def test_error_message_detail_without_exc_info():
    error = ValueError("Simple error")
    message = error_message_detail(error, error_detail=None)

    assert message == "Simple error"


# --------------------------------------------------
# Test: CallException string representation
# --------------------------------------------------

def test_call_exception_str():
    try:
        raise RuntimeError("Custom failure")
    except RuntimeError as e:
        exc = CallException(e, sys)

    message = str(exc)

    assert "Error in file" in message
    assert "line number" in message
    assert "Custom failure" in message

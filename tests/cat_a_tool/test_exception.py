import sys
import pytest
from backend.cat_a_tool.exception import error_message_detail, CallException
from backend.cat_a_tool.exception import CallException


def test_error_message_detail_with_exc_info():
    try:
        raise ValueError("Test error")
    except Exception as e:
        message = error_message_detail(e, sys)
        assert "Error in file" in message
        assert "Test error" in message


def test_error_message_detail_without_exc_info():
    error = ValueError("Simple error")
    message = error_message_detail(error, None)
    assert message == "Simple error"


def test_call_exception():
    exc = CallException("Failure", "Detail message")
    assert isinstance(exc, Exception)
    assert "Failure" in str(exc)
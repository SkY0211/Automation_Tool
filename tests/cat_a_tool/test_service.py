import pytest
from unittest.mock import patch

from backend.cat_a_tool import service


# --------------------------------------------------
# Helper: reset shared state before each test
# --------------------------------------------------

@pytest.fixture(autouse=True)
def reset_cat_a_state():
    service.cat_a_state.update({
        "state": "IDLE",
        "message": "",
        "progress": 0,
        "mo_connected": False,
        "mt_connected": False,
        "mo_serial": None,
        "mt_serial": None,
        "devices": []
    })


# --------------------------------------------------
# Test: FAIL if MO device not connected
# --------------------------------------------------

@patch("backend.cat_a_tool.service.threading.Thread")
def test_start_service_fails_when_mo_not_connected(mock_thread):
    config = {
        "test_type": "CALL",
        "mt_number": "1234567890",
        "iterations": 1,
        "call_duration": 10,
        "call_delay": 1,
    }

    service.start_cat_a_service(config)

    # Run the thread target immediately
    target = mock_thread.call_args.kwargs["target"]
    target()

    assert service.cat_a_state["state"] == "FAILED"
    assert service.cat_a_state["message"] == "MO device not connected"


# --------------------------------------------------
# Test: FAIL if MT number missing
# --------------------------------------------------

@patch("backend.cat_a_tool.service.threading.Thread")
def test_start_service_fails_when_mt_number_missing(mock_thread):
    service.cat_a_state["mo_connected"] = True
    service.cat_a_state["mt_connected"] = True
    service.cat_a_state["mo_serial"] = "MO123"
    service.cat_a_state["mt_serial"] = "MT123"

    config = {
        "test_type": "CALL",
        "iterations": 1,
        "call_duration": 10,
        "call_delay": 1,
    }

    service.start_cat_a_service(config)

    target = mock_thread.call_args.kwargs["target"]
    target()

    assert service.cat_a_state["state"] == "FAILED"
    assert service.cat_a_state["message"] == "MT phone number not saved"


# --------------------------------------------------
# Test: SUCCESS path (happy case)
# --------------------------------------------------

@patch("backend.cat_a_tool.service.start_cat_a_test")
@patch("backend.cat_a_tool.service.threading.Thread")
def test_start_service_success(mock_thread, mock_start_test):
    service.cat_a_state.update({
        "mo_connected": True,
        "mt_connected": True,
        "mo_serial": "MO123",
        "mt_serial": "MT123",
    })

    config = {
        "test_type": "CALL",
        "mt_number": "1234567890",
        "iterations": 2,
        "call_duration": 10,
        "call_delay": 1,
    }

    service.start_cat_a_service(config)

    # Execute thread immediately
    target = mock_thread.call_args.kwargs["target"]
    target()

    mock_start_test.assert_called_once()

    assert service.cat_a_state["state"] == "COMPLETED"
    assert service.cat_a_state["progress"] == 100
    assert service.cat_a_state["message"] == "CAT-A execution completed"

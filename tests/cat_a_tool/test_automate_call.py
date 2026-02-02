import threading
from unittest.mock import MagicMock, patch

import pytest

from backend.cat_a_tool.automate_call import CallTester, run_single_test, run_automation


# --------------------------------------------------
# FIXTURES
# --------------------------------------------------

@pytest.fixture
def minimal_config():
    return {
        "home": "HOME",
        "cred_mo": {"udid": "MO123", "Sim_Preference": "0"},
        "cred_mt": {"udid": "MT123", "Sim_Preference": "0"},
        "mt_number": "1234567890",
        "iterations": 1,
        "test_type": "CALL",
        "call_duration": 5,
        "call_delay": 1,
    }


@pytest.fixture
def dummy_barriers():
    return [
        threading.Barrier(1),
        threading.Barrier(1),
        threading.Barrier(1),
    ]


# --------------------------------------------------
# TEST: CallTester initialization (SAFE)
# --------------------------------------------------

@patch("backend.cat_a_tool.automate_call.get_latest_dir")
@patch("backend.cat_a_tool.automate_call.get_parent_dir")
@patch("backend.cat_a_tool.automate_call.openpyxl.Workbook")
@patch("backend.cat_a_tool.automate_call.CustomLogger")
def test_calltester_initialization(
    mock_logger,
    mock_workbook,
    mock_parent_dir,
    mock_latest_dir,
    dummy_barriers,
):
    mock_parent_dir.return_value = "/tmp"
    mock_latest_dir.return_value = "/tmp/reports"

    tester = CallTester(
        home="HOME",
        cred_mo={"udid": "MO123", "Sim_Preference": "0"},
        cred_mt={"udid": "MT123", "Sim_Preference": "0"},
        test_type="CALL",
        iterations=1,
        call_duration=5,
        call_delay=1,
        ph_no="1234567890",
        frame=None,
        mo_label="MO",
        mt_label="MT",
        barriers=dummy_barriers,
        no_of_devices=2,
    )

    assert tester.mo == "MO123"
    assert tester.mt == "MT123"
    assert tester.itr == 1
    assert tester.DURATION == 5
    assert tester.delay == 1


# --------------------------------------------------
# TEST: all_devices_connected logic
# --------------------------------------------------

@patch("backend.cat_a_tool.automate_call.count_connected_devices")
def test_all_devices_connected_success(mock_count, dummy_barriers):
    mock_count.return_value = (2, ["MO123", "MT123"])

    tester = MagicMock(spec=CallTester)
    tester.no_of_devices = 2
    tester.mo = "MO123"
    tester.mt = "MT123"
    tester.logger = MagicMock()

    result = CallTester.all_devices_connected(tester)
    assert result is True


# --------------------------------------------------
# TEST: run_single_test delegates correctly
# --------------------------------------------------

def test_run_single_test_calls_run_test():
    test_obj = MagicMock()
    queue = MagicMock()

    run_single_test(test_obj, queue)

    test_obj.run_test.assert_called_once_with(queue)


# --------------------------------------------------
# TEST: run_automation wiring (NO execution)
# --------------------------------------------------

@patch("backend.cat_a_tool.automate_call.CallTester")
def test_run_automation_creates_and_runs_tester(mock_tester, minimal_config):
    instance = mock_tester.return_value

    run_automation(minimal_config)

    mock_tester.assert_called_once()
    instance.run_test.assert_called_once()

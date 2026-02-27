from unittest.mock import patch, MagicMock
from backend.cat_a_tool.automate_call import CallTester


@patch("backend.cat_a_tool.automate_call.CustomLogger")   # 🔥 ADD THIS
@patch("backend.cat_a_tool.automate_call.openpyxl")
@patch("backend.cat_a_tool.automate_call.pd")
@patch("backend.cat_a_tool.automate_call.subprocess")
@patch("backend.cat_a_tool.automate_call.reconnect")
def test_calltester_init(
    mock_reconnect,
    mock_sub,
    mock_pd,
    mock_xl,
    mock_logger   # 🔥 ADD THIS PARAM
):

    cred_mo = {
        "udid": "device_mo",
        "username": "user",
        "password": "pass",
        "Sim_Preference": 1
    }

    cred_mt = {
        "udid": "device_mt",
        "username": "user",
        "password": "pass",
        "Sim_Preference": 1
    }

    fake_barrier_1 = MagicMock()
    fake_barrier_2 = MagicMock()
    fake_barrier_3 = MagicMock()

    tester = CallTester(
        home="home",
        cred_mo=cred_mo,
        cred_mt=cred_mt,
        test_type="type",
        iterations=1,
        call_duration=5,
        call_delay=1,
        ph_no="1234567890",
        frame=MagicMock(),
        mo_label=MagicMock(),
        mt_label=MagicMock(),
        barriers=[fake_barrier_1, fake_barrier_2, fake_barrier_3],
        no_of_devices=1
    )

    assert tester.mo == "device_mo"
    assert tester.mt == "device_mt"
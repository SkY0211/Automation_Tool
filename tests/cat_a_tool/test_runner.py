from unittest.mock import patch, MagicMock
from backend.cat_a_tool.runner import start_cat_a_test


@patch("backend.cat_a_tool.runner.CallTester")
@patch("backend.cat_a_tool.runner.CustomLogger")
def test_start_cat_a_test(mock_logger, mock_calltester):
    mock_instance = MagicMock()
    mock_calltester.return_value = mock_instance

    config = {
        "home": "path",
        "cred_mo": "mo",
        "cred_mt": "mt",
        "test_type": "type",
        "iterations": 1,
        "call_dur": 5
    }

    start_cat_a_test(config)

    mock_logger.assert_called()
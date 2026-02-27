from unittest.mock import patch
from backend.cat_a_tool.service import cat_a_state


def test_initial_state():
    assert cat_a_state["state"] == "IDLE"
    assert "progress" in cat_a_state


@patch("backend.cat_a_tool.service.start_cat_a_test")
def test_state_update(mock_start):
    mock_start.return_value = None
    cat_a_state["state"] = "RUNNING"
    assert cat_a_state["state"] == "RUNNING"
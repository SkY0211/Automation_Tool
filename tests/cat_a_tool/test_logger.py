from backend.cat_a_tool.logger import get_ui_logs


def test_get_ui_logs_returns_list():
    logs = get_ui_logs()
    assert isinstance(logs, list)

from unittest.mock import patch, MagicMock
from backend.cat_a_tool import utils


@patch("backend.cat_a_tool.utils.screeninfo.get_monitors")
def test_generate_window_locations(mock_monitors):
    mock_monitor = MagicMock()
    mock_monitor.width = 1920
    mock_monitor.height = 1080
    mock_monitors.return_value = [mock_monitor]

    locations = utils.generate_window_locations(2)
    assert isinstance(locations, list)


@patch("backend.cat_a_tool.utils.subprocess.run")
def test_subprocess_mock(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    result = utils.subprocess.run(["echo", "test"])
    assert result.returncode == 0
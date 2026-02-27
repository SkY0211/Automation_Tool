import os
import tempfile
from unittest.mock import patch
from backend.cat_a_tool.logger import CustomLogger, UI_LOG_BUFFER


@patch("backend.cat_a_tool.logger.get_latest_dir", return_value=tempfile.gettempdir())
@patch("backend.cat_a_tool.logger.get_parent_dir", return_value=tempfile.gettempdir())
def test_logger_creation(mock_parent, mock_latest):
    logger = CustomLogger("TEST")
    assert logger is not None


@patch("backend.cat_a_tool.logger.get_latest_dir", return_value=tempfile.gettempdir())
@patch("backend.cat_a_tool.logger.get_parent_dir", return_value=tempfile.gettempdir())
def test_logger_log_adds_ui_buffer(mock_parent, mock_latest):
    logger = CustomLogger("TEST")
    logger.log("Hello")
    assert len(UI_LOG_BUFFER) > 0
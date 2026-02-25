import os
import logging
import sys
from datetime import datetime
from backend.cat_a_tool.exception import CallException
from backend.cat_a_tool.utils import get_latest_dir, get_parent_dir

# ===============================
# UI LOG BUFFER (GLOBAL)
# ===============================
UI_LOG_BUFFER = []
MAX_UI_LOGS = 300

# ===============================
# SHARED LOG FOLDER (GLOBAL)
# ===============================
_CURRENT_LOG_FOLDER = None


class CustomLogger:
    def __init__(self, instance_name):
        self.instance_id = instance_name
        self.log_folder = self.get_latest_log_folder()
        self.logger = self.configure_logger()

    @staticmethod
    def get_latest_log_folder():
        global _CURRENT_LOG_FOLDER
        
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        logs_dir = os.path.join(desktop, "Automation_Tool_Logs")

        os.makedirs(logs_dir, exist_ok=True)

        # If we already have a folder for this test session, use it
        if _CURRENT_LOG_FOLDER and os.path.exists(_CURRENT_LOG_FOLDER):
            return _CURRENT_LOG_FOLDER

        # Create new folder with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder = os.path.join(logs_dir, timestamp)
        os.makedirs(folder, exist_ok=True)
        
        # Store it globally so all loggers use the same folder
        _CURRENT_LOG_FOLDER = folder
        return folder

    def configure_logger(self):
        logger_name = f"CAT_A_{self.instance_id}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # 🔴 VERY IMPORTANT

        # 🔥 ALWAYS reset handlers (fixes Flask + threads)
        logger.handlers.clear()

        log_file = os.path.join(self.log_folder, f"{self.instance_id}.log")

        # Ensure log file exists
        os.makedirs(self.log_folder, exist_ok=True)
        with open(log_file, "a", encoding="utf-8"):
            pass

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def log(self, message, error=None, level=logging.INFO):
        message = str(message)

        # Always log to file + console
        self.logger.log(level, message)

        # Push to UI buffer (filtered)
        noisy_keywords = [
            "Checking mCallState",
            "Polling",
            "Fetching ServiceState",  # Filter repetitive service state checks
        ]

        if not any(k in message for k in noisy_keywords):
            UI_LOG_BUFFER.append(message)
            if len(UI_LOG_BUFFER) > MAX_UI_LOGS:
                UI_LOG_BUFFER.pop(0)

        if error:
            err_msg = str(CallException(error, sys))
            self.logger.error(err_msg)
            UI_LOG_BUFFER.append(err_msg)
            if len(UI_LOG_BUFFER) > MAX_UI_LOGS:
                UI_LOG_BUFFER.pop(0)

        # Force flush (Windows fix)
        for handler in self.logger.handlers:
            try:
                handler.flush()
            except Exception:
                pass


# ===============================
# UI API HELPER
# ===============================
def get_ui_logs():
    return UI_LOG_BUFFER.copy()

def reset_log_folder():
    """Reset the shared log folder so next test creates a new folder"""
    global _CURRENT_LOG_FOLDER
    _CURRENT_LOG_FOLDER = None
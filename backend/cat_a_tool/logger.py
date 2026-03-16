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
        
        # ✅ Use standard Windows application data path
        programdata = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
        main_folder_name = "Automation Tool"
        main_dir = os.path.join(programdata, main_folder_name)
        os.makedirs(main_dir, exist_ok=True)

        # If we already have a folder for this test session, use it
        if _CURRENT_LOG_FOLDER and os.path.exists(_CURRENT_LOG_FOLDER):
            return _CURRENT_LOG_FOLDER

        # Create new timestamp folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_folder = os.path.join(main_dir, timestamp)
        
        # Create logs and reports subfolders
        logs_folder = os.path.join(session_folder, "logs")
        reports_folder = os.path.join(session_folder, "reports")
        
        os.makedirs(logs_folder, exist_ok=True)
        os.makedirs(reports_folder, exist_ok=True)
        
        # Store logs folder path globally
        _CURRENT_LOG_FOLDER = logs_folder
        return logs_folder

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

    def log(self, message, error=None, level=None):
        message = str(message)

        # ✅ Auto-detect level from message content if not explicitly provided
        if level is None:
            msg_lower = message.lower()
            if any(k in msg_lower for k in [
                "error", "failed", "fail", "exception", "not found",
                "invalid", "call dropped", "device disconnected", "abort"
            ]):
                level = logging.ERROR
            elif any(k in msg_lower for k in [
                "warning", "warn", "⚠️", "oos", "skipped", "skip",
                "disconnect", "paused", "stopped", "still oos", "retry"
            ]):
                level = logging.WARNING
            elif any(k in msg_lower for k in [
                "debug", "fetching", "checking", "polling", "collecting"
            ]):
                level = logging.DEBUG
            else:
                level = logging.INFO

        # Always log to file + console
        self.logger.log(level, message)

        # Push to UI buffer (filtered)
        noisy_keywords = [
            "Checking mCallState",
            "Polling",
            "Fetching ServiceState",
            "Queue update skipped"  # Filter repetitive service state checks
        ]

        if not any(k in message for k in noisy_keywords):
            level_tag = logging.getLevelName(level)
            ui_message = f"| {level_tag} | {message}"
            UI_LOG_BUFFER.append(ui_message)
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

def get_reports_folder():
    """Get the reports folder for the current test session"""
    global _CURRENT_LOG_FOLDER
    
    if _CURRENT_LOG_FOLDER:
        # logs folder is at: ...Automation_Tool_Logs/TIMESTAMP/logs
        # reports folder is at: ...Automation_Tool_Logs/TIMESTAMP/reports
        session_folder = os.path.dirname(_CURRENT_LOG_FOLDER)
        reports_folder = os.path.join(session_folder, "reports")
        os.makedirs(reports_folder, exist_ok=True)
        return reports_folder
    
    # Fallback - create new session
    programdata = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
    main_dir = os.path.join(programdata, "Automation Tool")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_folder = os.path.join(main_dir, timestamp)
    reports_folder = os.path.join(session_folder, "reports")
    os.makedirs(reports_folder, exist_ok=True)
    return reports_folder
def get_current_session_folder():
    """Get the current test session folder (parent of logs and reports)"""
    global _CURRENT_LOG_FOLDER
    
    if _CURRENT_LOG_FOLDER:
        # Return the parent folder (timestamp folder)
        return os.path.dirname(_CURRENT_LOG_FOLDER)
    
    # No active session
    return None
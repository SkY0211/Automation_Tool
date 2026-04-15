import os
import logging
import sys
from datetime import datetime

from backend.cat_f_tool.src.utility.exceptions import FPAException


# ── UI log bridge ─────────────────────────────────────────────────────────────
# Levels we surface to the live UI log box.  DEBUG is too noisy for the UI
# (raw serial bytes, hex dumps) so we show INFO and above, plus all DEBUG
# messages that contain useful keywords.
_UI_KEYWORDS = (
    "iteration", "dialing", "dial", "call", "ring", "answer", "ata",
    "pass", "fail", "paused", "resumed", "stopped", "oos", "oos zone",
    "reconnect", "device", "nw params", "collected", "holding",
    "start", "done", "error", "warning", "idle", "connecting",
)

def _push_to_ui(message: str, level: int):
    """Push a log line into service._ui_logs so the Flask /logs endpoint picks it up."""
    try:
        from backend.cat_f_tool.service import _ui_logs, _log_lock
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}"
        with _log_lock:
            _ui_logs.append(line)
            if len(_ui_logs) > 500:
                _ui_logs.pop(0)
    except Exception:
        pass   # never crash the automation because of a UI log failure


class CustomLogger:
    def __init__(self, instance_name, latest_log_dir):
        self.instance_id = instance_name
        self.log_folder  = latest_log_dir
        self.log_text    = self.configure_logger()

    def configure_logger(self):
        config_logger = logging.getLogger(f"CatF_Instance_{self.instance_id}")
        config_logger.setLevel(logging.DEBUG)

        for handler in config_logger.handlers:
            config_logger.removeHandler(handler)

        log_file     = os.path.join(self.log_folder, f"{self.instance_id}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        config_logger.addHandler(file_handler)

        return config_logger

    def log(self, message, error=None, level=logging.DEBUG):
        self.log_text.log(level, message)
        if error:
            self.log_text.log(logging.ERROR, FPAException(error, sys))

        # ── Bridge to UI log ──────────────────────────────────────────────────
        # Always push WARNING / ERROR / INFO to UI.
        # For DEBUG, only push if the message contains a useful keyword so the
        # UI doesn't get flooded with raw serial bytes.
        msg_lower = str(message).lower()
        if level >= logging.WARNING:
            _push_to_ui(str(message), level)
        elif level == logging.INFO:
            _push_to_ui(str(message), level)
        elif level == logging.DEBUG:
            if any(kw in msg_lower for kw in _UI_KEYWORDS):
                _push_to_ui(str(message), level)
"""
serial_spy.py
=============
Central factory for opening serial ports via pySerial's built-in spy:// URL
handler.  Every byte written to or read from the device is transparently
appended to a per-port trace file in the session log directory AND pushed
into the CAT-F live UI log so the operator can see raw device traffic in
real time.

Usage — replace:
    serial.Serial(port, baudrate=115200, timeout=2)
with:
    open_serial(port, baudrate=115200, timeout=2)

Everything else (read, write, close, context manager) works identically
because the returned object IS a pySerial Serial instance.
"""

import os
import io
import threading
from datetime import datetime

import serial


# ── Per-session trace files, one per port ────────────────────────────────────
# Maps  port_name → absolute path of its trace file for the current session.
# Cleared at the start of each test run by reset_spy_files().
_spy_files: dict[str, str] = {}
_spy_lock = threading.Lock()


def reset_spy_files():
    """Call this at the start of each test run to clear the port→file map."""
    with _spy_lock:
        _spy_files.clear()


def _trace_path(port: str) -> str:
    """
    Return (and register) the trace-file path for *port* in the current
    session log directory.  Creates the file on first call for this port.
    """
    with _spy_lock:
        if port in _spy_files:
            return _spy_files[port]

        # Import here to avoid circular imports at module load time
        from backend.cat_f_tool.src.data.dir_paths import Paths

        log_dir = getattr(Paths, "latest_log_dir_path", "") or ""
        if not log_dir:
            import tempfile
            log_dir = tempfile.gettempdir()

        # Sanitise port name for use as a filename (COM9 → COM9, etc.)
        safe_port = port.replace("/", "_").replace("\\", "_").replace(":", "")
        path = os.path.join(log_dir, f"spy_{safe_port}.log")
        _spy_files[port] = path
        return path


class _UiBridge(io.RawIOBase):
    """
    A file-like object passed to spy:// as the output sink.
    Every line written by pySerial's spy handler is:
      1. Written to the per-port trace file on disk.
      2. Pushed into _ui_logs in service.py so it appears in the live log box
         (only meaningful lines — raw hex dumps are filtered out).
    """

    def __init__(self, port: str, trace_path: str):
        self._port       = port
        self._trace_path = trace_path
        self._file       = open(trace_path, "a", encoding="utf-8", errors="replace")
        self._buf        = ""

    # ── io.RawIOBase interface ────────────────────────────────────────────────

    def write(self, b):
        if isinstance(b, (bytes, bytearray)):
            text = b.decode("utf-8", errors="replace")
        else:
            text = str(b)
        self._file.write(text)
        self._file.flush()
        self._push_ui(text)
        return len(b)

    def readable(self):  return False
    def writable(self):  return True
    def seekable(self):  return False

    def close(self):
        if not self.closed:
            try:
                self._file.close()
            except Exception:
                pass
            super().close()

    # ── UI bridge ─────────────────────────────────────────────────────────────

    def _push_ui(self, text: str):
        """
        Push meaningful spy lines to the live UI log.
        pySerial spy writes lines like:
            write: b'ATD7039539959;\r\n'
            read:  b'\r\nOK\r\n'
        We surface write/read lines and skip raw hex dumps.
        """
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            # Only surface write / read / call lines — skip internal spy headers
            lower = line.lower()
            if not any(kw in lower for kw in ("write:", "read:", "open", "close")):
                continue
            # Strip the b'...' wrapper to show clean AT text
            msg = f"[{self._port}] {line}"
            try:
                from backend.cat_f_tool.service import _ui_logs, _log_lock
                ts = datetime.now().strftime("%H:%M:%S")
                entry = f"[{ts}] {msg}"
                with _log_lock:
                    _ui_logs.append(entry)
                    if len(_ui_logs) > 500:
                        _ui_logs.pop(0)
            except Exception:
                pass


# ── Public API ────────────────────────────────────────────────────────────────

def open_serial(port: str, baudrate: int = 115200, timeout=2, **kwargs) -> serial.Serial:
    """
    Open *port* with a transparent spy:// wrapper.

    All reads and writes are mirrored to:
      • artifacts/logs/<session>/spy_<PORT>.log   (disk trace file)
      • The CAT-F live UI log box                 (filtered, human-readable lines)

    Returns a standard pySerial Serial object — use it exactly like
    serial.Serial(...).
    """
    trace = _trace_path(port)
    bridge = _UiBridge(port, trace)

    # spy:// URL format:  spy://PORT?output=<file-like>
    # pySerial accepts a file-like object for the output option.
    url = f"spy://{port}?color=False"
    try:
        ser = serial.serial_for_url(
            url,
            baudrate=baudrate,
            timeout=timeout,
            output=bridge,
            **kwargs,
        )
        return ser
    except Exception:
        # Fallback: if spy:// fails for any reason, open normally so the
        # automation never breaks because of logging.
        return serial.Serial(port, baudrate=baudrate, timeout=timeout, **kwargs)
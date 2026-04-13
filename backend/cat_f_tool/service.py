"""
CAT-F Service
=============
Wraps the original CAT-F CallTester logic into a Flask-friendly service layer,
mirroring the same pattern used by cat_a_tool/service.py.

No CAT-A logic is touched. Only CAT-F state lives here.
"""

import threading
import os
import sys
from datetime import datetime

# ── Shared state dict (read by Flask API endpoints) ──────────────────────────
cat_f_state = {
    "state": "IDLE",        # IDLE | RUNNING | PAUSED | STOPPED | DONE | ERROR
    "message": "",
    "progress": 0,
    "current_iteration": 0,
    "total_iterations": 0,
    "test_running": False,
    "paused": False,
    "mo_port": None,
    "mt_port": None,
    "mo_phone": None,
    "mt_phone": None,
    "test_type": None,
    "device_disconnected": False,
    "disconnected_device": None,
    "error": None,
    # OOS (Out of Service) alert
    "oos_detected": False,
    "oos_devices": [],
    # Unique ID per test run — lets OOS wait detect a new test was started
    "test_id": 0,
}

# ── Threading events (pause / resume / stop) ─────────────────────────────────
_pause_event  = threading.Event()
_resume_event = threading.Event()
_stop_event   = threading.Event()

_ui_logs  = []
_log_lock = threading.Lock()


def _add_log(msg: str):
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    with _log_lock:
        _ui_logs.append(line)
        if len(_ui_logs) > 500:
            _ui_logs.pop(0)
    print(f"[CAT-F] {line}")


def get_ui_logs():
    with _log_lock:
        return list(_ui_logs)


# ── Internal runner (runs in its own thread) ─────────────────────────────────

def _run_cat_f(config: dict):
    """
    Core CAT-F test runner.
    Populates the original CAT-F data-classes from the web config dict,
    then runs CallTester.run_test() exactly as the original Tkinter app did —
    without any Tkinter dependency.
    """

    # ── Pull config ──────────────────────────────────────────────────────────
    mo_port       = config.get("mo_port", "")
    mt_port       = config.get("mt_port", "")
    mo_phone      = config.get("mo_phone", "")
    mt_phone      = config.get("mt_phone", "")
    mo_sw         = config.get("mo_sw", "N/A")
    mt_sw         = config.get("mt_sw", "N/A")
    mo_imei       = config.get("mo_imei", "N/A")
    mt_imei       = config.get("mt_imei", "N/A")
    test_type     = config.get("test_type", "MO calls")
    iterations    = int(config.get("iterations", 10))
    call_duration = int(config.get("call_duration", 30))
    call_delay    = int(config.get("call_delay", 5))
    country_code  = config.get("country_code", "+91")

    cat_f_state["test_id"] = cat_f_state.get("test_id", 0) + 1
    cat_f_state.update({
        "state":             "RUNNING",
        "message":           "Test started",
        "progress":          0,
        "current_iteration": 0,
        "total_iterations":  iterations,
        "test_running":      True,
        "paused":            False,
        "mo_port":           mo_port,
        "mt_port":           mt_port,
        "mo_phone":          mo_phone,
        "mt_phone":          mt_phone,
        "test_type":         test_type,
        "device_disconnected": False,
        "disconnected_device": None,
        "error":             None,
        "oos_detected":      False,
        "oos_devices":       [],
    })

    _add_log(f"CAT-F starting — {test_type}, {iterations} iterations, "
             f"{call_duration}s duration, {call_delay}s delay")

    # ── Import CAT-F backend ─────────────────────────────────────────────────
    try:
        from backend.cat_f_tool.src.data.device_info       import DeviceInfo
        from backend.cat_f_tool.src.data.test_credentials  import TestCred
        from backend.cat_f_tool.src.data.dir_paths         import Paths
        from backend.cat_f_tool.src.utility.utils          import create_folders
        from backend.cat_f_tool.src.utility.logger         import CustomLogger as CatFLogger
        from backend.cat_f_tool.src.backend.call_conroller import CallTester
        from queue import Queue

    except ImportError as e:
        msg = f"CAT-F import error: {e}"
        _add_log(msg)
        cat_f_state.update({"state": "ERROR", "message": msg, "test_running": False})
        return

    # ── Populate data-classes (replaces Tkinter-based user input) ────────────
    def _normalize_phone(number, code):
        """
        Strip any existing country-code prefix so every phone number is
        stored in local format (digits only, no +CC prefix).
        dial_number() in helper.py re-adds the country code on its
        international retry, so storing the prefix here would produce
        a double-prefixed number like +9191XXXXXXXXXX which the network
        rejects as invalid -- causing MT->MO calls to fail.
        """
        number    = number.strip()
        code_bare = code.lstrip("+")
        if number.startswith("+"):
            number = number.lstrip("+")
        if number.startswith(code_bare):
            number = number[len(code_bare):]
        return number

    DeviceInfo.country = ""
    DeviceInfo.code    = country_code
    DeviceInfo.dev1    = {
        "Software Version": mo_sw,
        "IMEI":             mo_imei,
        "Phone Number":     _normalize_phone(mo_phone, country_code),
        "AT Port":          mo_port,
    }
    DeviceInfo.dev2    = {
        "Software Version": mt_sw,
        "IMEI":             mt_imei,
        "Phone Number":     _normalize_phone(mt_phone, country_code),
        "AT Port":          mt_port,
    }

    TestCred.call_type    = "voice"
    TestCred.test_type    = test_type
    TestCred.country_code = country_code
    TestCred.iterations   = iterations
    TestCred.call_duration = call_duration
    TestCred.call_delay   = call_delay

    # ── Create output folders ────────────────────────────────────────────────
    create_folders()
    _add_log(f"Output folder: {Paths.latest_report_dir_path}")

    logger = CatFLogger("backend", Paths.latest_log_dir_path)

    # ── Prepare threading events for CallTester ──────────────────────────────
    orig_pause_event  = threading.Event()
    orig_resume_event = threading.Event()
    orig_end_event    = threading.Event()

    _stop_event.clear()
    _pause_event.clear()
    _resume_event.clear()

    # ── Run test ─────────────────────────────────────────────────────────────
    try:
        tester = CallTester(
            home=None,                      # No Tkinter widget needed
            progress_frame=None,            # No Tkinter widget needed
            resume_event=orig_resume_event,
            pause_event=orig_pause_event,
            end_test_event=orig_end_event,
        )

        queue = Queue()

        def _monitor():
            """
            Runs in a side-thread.
            Reads completed-iteration numbers from the queue and updates
            cat_f_state so the Flask /status endpoint always has fresh data.
            Also relays our pause/resume/stop events into the original events.
            """
            import time
            while True:
                # Drain completed iterations from queue
                while not queue.empty():
                    itr = queue.get()
                    pct = int((itr / iterations) * 100)
                    cat_f_state.update({
                        "current_iteration": itr,
                        "progress":          pct,
                        "message":           f"Iteration {itr}/{iterations} done",
                    })
                    _add_log(f"Iteration {itr}/{iterations} complete")

                # Relay stop
                if _stop_event.is_set():
                    orig_end_event.set()
                    return

                # Relay pause
                if _pause_event.is_set() and not orig_pause_event.is_set():
                    orig_pause_event.set()

                # Relay resume
                if _resume_event.is_set() and orig_pause_event.is_set():
                    orig_pause_event.clear()
                    orig_resume_event.set()
                    _resume_event.clear()

                time.sleep(0.3)

        monitor_thread = threading.Thread(target=_monitor, daemon=True)
        monitor_thread.start()

        # Blocks until CallTester.run_test() finishes
        tester.run_test(queue)

        if _stop_event.is_set():
            cat_f_state.update({
                "state":        "STOPPED",
                "message":      "Test stopped by user",
                "test_running": False,
                "paused":       False,
            })
            _add_log("Test stopped by user")
        else:
            cat_f_state.update({
                "state":        "DONE",
                "message":      "Test completed successfully",
                "progress":     100,
                "test_running": False,
                "paused":       False,
            })
            _add_log(f"Test completed. Report: {Paths.latest_report_dir_path}")

    except Exception as e:
        import traceback
        err = traceback.format_exc()
        _add_log(f"CAT-F ERROR: {e}\n{err}")
        cat_f_state.update({
            "state":        "ERROR",
            "message":      str(e),
            "test_running": False,
            "paused":       False,
            "error":        str(e),
        })


# ── Public API (called by Flask routes in app.py) ────────────────────────────

def start_cat_f_service(config: dict):
    """Start CAT-F test in a background thread."""
    if cat_f_state.get("test_running"):
        return {"status": "error", "message": "A CAT-F test is already running"}

    _stop_event.clear()
    _pause_event.clear()
    _resume_event.clear()

    t = threading.Thread(target=_run_cat_f, args=(config,), daemon=True)
    t.start()
    return {"status": "started"}


def pause_cat_f_test():
    if not cat_f_state.get("test_running"):
        return {"status": "error", "message": "No test is running"}
    if cat_f_state.get("paused"):
        return {"status": "error", "message": "Test is already paused"}
    _pause_event.set()
    cat_f_state["paused"] = True
    cat_f_state["state"]  = "PAUSED"
    _add_log("Test paused")
    return {"status": "success", "message": "Test paused"}


def resume_cat_f_test():
    if not cat_f_state.get("paused"):
        return {"status": "error", "message": "Test is not paused"}
    _resume_event.set()
    _pause_event.clear()
    cat_f_state["paused"] = False
    cat_f_state["state"]  = "RUNNING"
    _add_log("Test resumed")
    return {"status": "success", "message": "Test resumed"}


def stop_cat_f_test():
    if not cat_f_state.get("test_running"):
        return {"status": "error", "message": "No test is running"}
    _stop_event.set()
    # Also clear any pending OOS alert so the UI unblocks immediately
    cat_f_state["oos_detected"] = False
    cat_f_state["oos_devices"]  = []
    _add_log("Stop requested")
    return {"status": "success", "message": "Stop signal sent"}


def clear_cat_f_oos_alert():
    """Clear the CAT-F OOS (Out of Service) alert flag."""
    cat_f_state["oos_detected"] = False
    cat_f_state["oos_devices"]  = []
    return {"status": "success", "message": "OOS alert cleared"}


def get_current_session_folder():
    """Return the latest CAT-F report folder (for the open-folder button)."""
    try:
        from backend.cat_f_tool.src.data.dir_paths import Paths
        return Paths.latest_report_dir_path
    except Exception:
        return None
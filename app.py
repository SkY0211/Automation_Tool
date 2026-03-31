import sys
import os
import threading
import webview
from flask import Flask, send_from_directory, request, jsonify
from backend.cat_a_tool.progress_state import progress_data

# =====================================================
# PATH FIX (IMPORTANT FOR WINDOWS / NUITKA)
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# =====================================================
# CAT-A BACKEND IMPORTS (unchanged)
# =====================================================

from backend.cat_a_tool.service import (
    start_cat_a_service,
    start_device_monitor,
    cat_a_state,
    pause_test,
    resume_test,
    stop_test,
    clear_disconnect_alert,
    clear_oos_alert
)

from backend.cat_a_tool.logger import get_ui_logs

# =====================================================
# CAT-F BACKEND IMPORTS (new)
# =====================================================

from backend.cat_f_tool.service import (
    start_cat_f_service,
    cat_f_state,
    pause_cat_f_test,
    resume_cat_f_test,
    stop_cat_f_test,
    get_current_session_folder as get_cat_f_session_folder,
)
from backend.cat_f_tool.service import get_ui_logs as get_cat_f_logs

# =====================================================
# RESOURCE PATH (FOR EXE / NUITKA)
# =====================================================

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(BASE_DIR, relative_path)

WEBUI_DIR = resource_path("webui")

# =====================================================
# FLASK APP
# =====================================================

app = Flask(
    __name__,
    static_folder=WEBUI_DIR,
    static_url_path=""
)

@app.after_request
def disable_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/")
def index():
    return send_from_directory(WEBUI_DIR, "index.html")

# =====================================================
# CAT-A API ENDPOINTS (unchanged)
# =====================================================

@app.route("/api/cat-a/start", methods=["POST"])
def api_start_cat_a():
    config = request.json
    print("=" * 60)
    print("CAT-A START API HIT:", config)
    print("=" * 60)
    start_cat_a_service(config)
    return jsonify({"status": "started"})

@app.route("/api/cat-a/status", methods=["GET"])
def api_cat_a_status():
    return jsonify({
        "state": cat_a_state.get("state", "IDLE"),
        "message": cat_a_state.get("message", ""),
        "progress": cat_a_state.get("progress", 0),
        "mo_connected": cat_a_state.get("mo_connected", False),
        "mt_connected": cat_a_state.get("mt_connected", False),
        "mo_serial": cat_a_state.get("mo_serial"),
        "mt_serial": cat_a_state.get("mt_serial"),
        "pairs": cat_a_state.get("pairs", []),
        "devices": cat_a_state.get("devices", []),
        "paused": cat_a_state.get("paused", False),
        "test_running": cat_a_state.get("test_running", False),
        "device_disconnected": cat_a_state.get("device_disconnected", False),
        "disconnected_device": cat_a_state.get("disconnected_device"),
        "current_iteration": cat_a_state.get("current_iteration", 0),
        "total_iterations": cat_a_state.get("total_iterations", 0),
        "oos_detected": cat_a_state.get("oos_detected", False),
        "oos_devices": cat_a_state.get("oos_devices", [])
    })

@app.route("/api/cat-a/logs", methods=["GET"])
def api_cat_a_logs():
    return jsonify(get_ui_logs())

@app.route("/api/cat-a/devices", methods=["GET"])
def api_cat_a_devices():
    return jsonify({
        "mo_connected": cat_a_state["mo_connected"],
        "mt_connected": cat_a_state["mt_connected"],
        "mo_serial": cat_a_state["mo_serial"],
        "mt_serial": cat_a_state["mt_serial"],
    })

@app.route("/api/cat-a/progress")
def cat_a_progress():
    return jsonify(progress_data)

@app.route('/api/cat-a/pause', methods=['POST'])
def pause_cat_a_test():
    result = pause_test()
    return jsonify(result), 200 if result["status"] == "success" else 400

@app.route('/api/cat-a/resume', methods=['POST'])
def resume_cat_a_test():
    result = resume_test()
    return jsonify(result), 200 if result["status"] == "success" else 400

@app.route('/api/cat-a/stop', methods=['POST'])
def stop_cat_a_test():
    result = stop_test()
    return jsonify(result), 200 if result["status"] == "success" else 400

@app.route('/api/cat-a/clear-disconnect', methods=['POST'])
def clear_disconnect():
    try:
        result = clear_disconnect_alert()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/cat-a/clear-oos', methods=['POST'])
def clear_oos():
    try:
        result = clear_oos_alert()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/cat-a/open-folder', methods=['POST'])
def open_output_folder():
    try:
        from backend.cat_a_tool.logger import get_current_session_folder
        import subprocess
        session_folder = get_current_session_folder()
        if session_folder and os.path.exists(session_folder):
            subprocess.Popen(
                f'explorer "{session_folder}"',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return jsonify({"status": "success", "message": "Folder opened", "path": session_folder}), 200
        else:
            return jsonify({"status": "error", "message": "No active test session"}), 404
    except Exception as e:
        print(f"Error opening folder: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/cat-a/detect-device', methods=['POST'])
def detect_device():
    try:
        data = request.json
        already_connected = data.get('already_connected', [])
        import subprocess
        import re
        from backend.cat_a_tool.utils import get_device_name, get_android_version
        from backend.cat_a_tool.logger import CustomLogger
        logger = CustomLogger("device_detection")
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        output = result.stdout
        logger.log(f"ADB devices output: {output}")
        logger.log(f"Already connected: {already_connected}")
        lines = output.strip().split('\n')[1:]
        device_serials = []
        for line in lines:
            line = line.strip()
            if line and '\tdevice' in line:
                serial = line.split('\t')[0]
                device_serials.append(serial)
        logger.log(f"Found devices: {device_serials}")
        new_device = None
        for device_serial in device_serials:
            if device_serial not in already_connected:
                new_device = device_serial
                logger.log(f"New device found: {new_device}")
                break
        if not new_device:
            logger.log("No new device found")
            return jsonify({"status": "error", "device": "NotFound", "message": "No new device found"}), 200
        device_name = get_device_name(new_device, logger)
        android_version = get_android_version(new_device, logger)
        logger.log(f"Device info - Name: {device_name}, Version: {android_version}")
        return jsonify({
            "status": "success",
            "device": {"serial": new_device, "name": device_name, "android_version": android_version}
        }), 200
    except Exception as e:
        print(f"Error in detect_device: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# =====================================================
# CAT-F API ENDPOINTS
# =====================================================

@app.route("/api/cat-f/start", methods=["POST"])
def api_start_cat_f():
    config = request.json
    print("=" * 60)
    print("CAT-F START API HIT:", config)
    print("=" * 60)
    result = start_cat_f_service(config)
    return jsonify(result)

@app.route("/api/cat-f/status", methods=["GET"])
def api_cat_f_status():
    return jsonify({
        "state":               cat_f_state.get("state", "IDLE"),
        "message":             cat_f_state.get("message", ""),
        "progress":            cat_f_state.get("progress", 0),
        "test_running":        cat_f_state.get("test_running", False),
        "paused":              cat_f_state.get("paused", False),
        "current_iteration":   cat_f_state.get("current_iteration", 0),
        "total_iterations":    cat_f_state.get("total_iterations", 0),
        "mo_port":             cat_f_state.get("mo_port"),
        "mt_port":             cat_f_state.get("mt_port"),
        "test_type":           cat_f_state.get("test_type"),
        "device_disconnected": cat_f_state.get("device_disconnected", False),
        "disconnected_device": cat_f_state.get("disconnected_device"),
        "error":               cat_f_state.get("error"),
    })

@app.route("/api/cat-f/logs", methods=["GET"])
def api_cat_f_logs():
    return jsonify(get_cat_f_logs())

@app.route("/api/cat-f/pause", methods=["POST"])
def api_pause_cat_f():
    result = pause_cat_f_test()
    return jsonify(result), 200 if result["status"] == "success" else 400

@app.route("/api/cat-f/resume", methods=["POST"])
def api_resume_cat_f():
    result = resume_cat_f_test()
    return jsonify(result), 200 if result["status"] == "success" else 400

@app.route("/api/cat-f/stop", methods=["POST"])
def api_stop_cat_f():
    result = stop_cat_f_test()
    return jsonify(result), 200 if result["status"] == "success" else 400

@app.route("/api/cat-f/open-folder", methods=["POST"])
def open_cat_f_output_folder():
    try:
        import subprocess
        session_folder = get_cat_f_session_folder()
        if session_folder and os.path.exists(session_folder):
            subprocess.Popen(
                f'explorer "{session_folder}"',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return jsonify({"status": "success", "message": "Folder opened", "path": session_folder}), 200
        return jsonify({"status": "error", "message": "No active test session"}), 404
    except Exception as e:
        print(f"Error opening CAT-F folder: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/cat-f/detect-device", methods=["POST"])
def catf_detect_device():
    """
    Auto-detect a serial COM port and extract device info via AT commands.
    Mirrors the original CAT-F find_at_port + extract_device_info flow.
    Body: { "checked_ports": ["COM11"] }   <- ports already used
    """
    try:
        data          = request.json or {}
        checked_ports = data.get("checked_ports", [])

        from backend.cat_f_tool.src.utility.utils  import find_at_port, extract_device_info
        from backend.cat_f_tool.src.utility.logger import CustomLogger as CatFLogger
        from backend.cat_f_tool.src.data.dir_paths import Paths
        import tempfile, os

        # Use a temp dir for the logger if no session folder exists yet
        log_dir = Paths.latest_log_dir_path if Paths.latest_log_dir_path else tempfile.gettempdir()
        logger  = CatFLogger("catf_detect", log_dir)

        at_port = find_at_port(list(checked_ports), logger)

        if at_port is None:
            return jsonify({
                "status":  "error",
                "message": "No device found. Please make sure the device is properly connected and try again."
            }), 200

        device_info = extract_device_info(at_port, logger)

        return jsonify({
            "status":      "success",
            "at_port":     at_port,
            "sw_version":  device_info.get("Software Version", "Not found"),
            "imei":        device_info.get("IMEI",             "Not found"),
            "phone_number": device_info.get("Phone Number",    "Not found"),
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# =====================================================
# FLASK RUNNER
# =====================================================

def start_flask():
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )

# =====================================================
# DESKTOP APP ENTRY POINT
# =====================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AUTOMATION TOOL STARTING")
    print("=" * 60)

    start_device_monitor()

    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    print("✅ Flask server started on http://127.0.0.1:5000")
    print("✅ Device monitor started")
    print("=" * 60)

    webview.create_window(
        title="Automation Tool – Integration Dashboard",
        url="http://127.0.0.1:5000",
        width=1200,
        height=750,
        resizable=True
    )

    webview.start()
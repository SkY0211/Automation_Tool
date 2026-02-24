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
# BACKEND IMPORTS (SINGLE SOURCE) 
# =====================================================

from backend.cat_a_tool.service import (
    start_cat_a_service,
    start_device_monitor,
    cat_a_state,
    pause_test,
    resume_test,
    stop_test,
    clear_disconnect_alert,
    clear_oos_alert          # ✅ NEW: OOS alert function
)

from backend.cat_a_tool.logger import get_ui_logs

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
# CAT-A API ENDPOINTS (SINGLE, CLEAN SET)
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
    # ✅ CRITICAL FIX: DO NOT call update_cat_a_device_state()
    # It uses alphabetical order which breaks connection order!
    # The device monitor in service.py already updates cat_a_state correctly
    
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
        # ✅ NEW: OOS fields
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

# =====================================================
# PAUSE/RESUME/STOP ENDPOINTS
# =====================================================

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
    """Clear device disconnection alert"""
    try:
        result = clear_disconnect_alert()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ✅ NEW: OOS alert endpoint
@app.route('/api/cat-a/clear-oos', methods=['POST'])
def clear_oos():
    """Clear OOS (Out of Service) alert"""
    try:
        result = clear_oos_alert()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ✅ NEW: Device detection endpoint for manual connection flow
@app.route('/api/cat-a/detect-device', methods=['POST'])
def detect_device():
    """Detect newly connected device (excluding already connected ones)"""
    try:
        data = request.json
        already_connected = data.get('already_connected', [])
        
        import subprocess
        import re
        from backend.cat_a_tool.utils import get_device_name, get_android_version
        from backend.cat_a_tool.logger import CustomLogger
        
        logger = CustomLogger("device_detection")
        
        # Get all connected devices
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        output = result.stdout
        
        logger.log(f"ADB devices output: {output}")
        logger.log(f"Already connected: {already_connected}")
        
        # Parse device serials - skip the header line
        lines = output.strip().split('\n')[1:]  # Skip "List of devices attached"
        device_serials = []
        
        for line in lines:
            line = line.strip()
            if line and '\tdevice' in line:  # Only lines with "device" status
                serial = line.split('\t')[0]
                device_serials.append(serial)
        
        logger.log(f"Found devices: {device_serials}")
        
        # Filter out already connected devices
        new_device = None
        for device_serial in device_serials:
            if device_serial not in already_connected:
                new_device = device_serial
                logger.log(f"New device found: {new_device}")
                break
        
        if not new_device:
            logger.log("No new device found")
            return jsonify({
                "status": "error",
                "device": "NotFound",
                "message": "No new device found"
            }), 200
        
        # Get device info
        device_name = get_device_name(new_device, logger)
        android_version = get_android_version(new_device, logger)
        
        logger.log(f"Device info - Name: {device_name}, Version: {android_version}")
        
        return jsonify({
            "status": "success",
            "device": {
                "serial": new_device,
                "name": device_name,
                "android_version": android_version
            }
        }), 200
        
    except Exception as e:
        print(f"Error in detect_device: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

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

    # 🔥 START DEVICE MONITOR ONCE
    start_device_monitor()

    # 🔥 START FLASK IN BACKGROUND
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    print("✅ Flask server started on http://127.0.0.1:5000")
    print("✅ Device monitor started")
    print("=" * 60)

    # 🔥 START DESKTOP WINDOW
    webview.create_window(
        title="Automation Tool – Integration Dashboard",
        url="http://127.0.0.1:5000",
        width=1200,
        height=750,
        resizable=True
    )

    webview.start()
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
    cat_a_state
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
    print("CAT-A START API HIT:", config)
    start_cat_a_service(config)
    return jsonify({"status": "started"})

@app.route("/api/cat-a/status", methods=["GET"])
def api_cat_a_status():
    return jsonify(cat_a_state)

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
    from backend.cat_a_tool.progress_state import progress_data
    return jsonify(progress_data)



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

    # 🔥 START DEVICE MONITOR ONCE
    start_device_monitor()

    # 🔥 START FLASK IN BACKGROUND
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # 🔥 START DESKTOP WINDOW
    webview.create_window(
        title="Automation Tool – Integration Dashboard",
        url="http://127.0.0.1:5000",
        width=1200,
        height=750,
        resizable=True
    )

    webview.start()

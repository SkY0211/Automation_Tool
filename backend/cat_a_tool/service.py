import threading
import subprocess
import time

from backend.cat_a_tool.runner import start_cat_a_test

# =====================================================
# CAT-A shared runtime state (SINGLE SOURCE OF TRUTH)
# =====================================================

cat_a_state = {
    "state": "IDLE",  # IDLE, RUNNING, PAUSED, COMPLETED, FAILED
    "message": "",
    "progress": 0,

    # Backward compatible (pair 1)
    "mo_connected": False,
    "mt_connected": False,
    "mo_serial": None,
    "mt_serial": None,

    "connection_order": [],      # Connection order tracking

    # NEW: multi-device support
    "devices": [],               # raw adb list
    "pairs": [],                 # derived MO–MT pairs
    
    # NEW: Pause/Resume control
    "paused": False,
    "stop_requested": False,
    
    # NEW: Device disconnection alert
    "device_disconnected": False,
    "disconnected_device": None,
    
    # NEW: Test tracking
    "test_running": False,
    "current_iteration": 0,
    "total_iterations": 0
}

def update_pairs_from_devices():
    """
    UI helper: derive MO–MT pairs from connected devices
    Does NOT change automation logic
    """
    devices = cat_a_state.get("devices", [])

    # 🔧 FIX: If no devices, return empty pairs list
    if not devices:
        cat_a_state["pairs"] = []
        return

    pairs = []
    pair_index = 1
    
    for i in range(0, len(devices), 2):
        mo = devices[i] if i < len(devices) else None
        mt = devices[i + 1] if i + 1 < len(devices) else None

        pair = {
            "pair_id": pair_index,
            "mo": {
                "name": f"MO{pair_index}",
                "serial": mo,
                "connected": bool(mo)
            },
            "mt": {
                "name": f"MT{pair_index}",
                "serial": mt,
                "connected": bool(mt)
            },
            # 🔧 FIX: Add flattened connection flags for frontend
            "mo_connected": bool(mo),
            "mt_connected": bool(mt)
        }

        pairs.append(pair)
        pair_index += 1

    cat_a_state["pairs"] = pairs


# =====================================================
# REAL DEVICE DETECTION (ADB)
# =====================================================

def detect_devices():
    """
    Detect connected devices and maintain connection order
    First connected device = MO, Second = MT
    Also monitors for disconnection during test
    """
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True
        )

        lines = result.stdout.strip().split("\n")[1:]
        current_devices = [line.split()[0] for line in lines if "device" in line]

        # 🔧 FIX: Initialize connection_order if it doesn't exist
        if "connection_order" not in cat_a_state:
            cat_a_state["connection_order"] = []
        
        existing_order = cat_a_state["connection_order"]
        
        # ✅ NEW: Check for device disconnection during test
        if cat_a_state.get("test_running", False):
            mo_serial = cat_a_state.get("mo_serial")
            mt_serial = cat_a_state.get("mt_serial")
            
            # Check if MO or MT disconnected during test
            if mo_serial and mo_serial not in current_devices:
                cat_a_state["device_disconnected"] = True
                cat_a_state["disconnected_device"] = "MO"
                print(f"⚠️ ALERT: MO device {mo_serial} disconnected during test!")
                
            if mt_serial and mt_serial not in current_devices:
                cat_a_state["device_disconnected"] = True
                cat_a_state["disconnected_device"] = "MT"
                print(f"⚠️ ALERT: MT device {mt_serial} disconnected during test!")
        
        # 🔧 FIX: If NO devices connected, CLEAR everything
        if not current_devices:
            cat_a_state["connection_order"] = []
            cat_a_state["devices"] = []
            cat_a_state["mo_serial"] = None
            cat_a_state["mt_serial"] = None
            cat_a_state["mo_connected"] = False
            cat_a_state["mt_connected"] = False
            cat_a_state["pairs"] = []
            
            print("🔍 DEVICE DETECTION: NO DEVICES CONNECTED - STATE CLEARED")
            return
        
        # 🔧 FIX: Remove disconnected devices from order
        existing_order = [d for d in existing_order if d in current_devices]
        
        # Add newly connected devices to the end (preserves connection order)
        for device in current_devices:
            if device not in existing_order:
                existing_order.append(device)
        
        cat_a_state["connection_order"] = existing_order
        
        # ✅ USE CONNECTION ORDER instead of alphabetical order
        devices = cat_a_state["connection_order"]
        
        cat_a_state["devices"] = devices

        # ✅ CORRECT: First connected = MO, Second connected = MT
        cat_a_state["mo_serial"] = devices[0] if len(devices) >= 1 else None
        cat_a_state["mt_serial"] = devices[1] if len(devices) >= 2 else None

        # 🔧 FIX: Update pairs BEFORE setting connection flags
        update_pairs_from_devices()

        # 🔧 FIX: Explicitly set connection status based on serial presence
        cat_a_state["mo_connected"] = cat_a_state["mo_serial"] is not None
        cat_a_state["mt_connected"] = cat_a_state["mt_serial"] is not None

    except Exception as e:
        # 🔧 FIX: On error, explicitly clear all connection states
        cat_a_state["mo_connected"] = False
        cat_a_state["mt_connected"] = False
        cat_a_state["mo_serial"] = None
        cat_a_state["mt_serial"] = None
        cat_a_state["devices"] = []
        cat_a_state["pairs"] = []
        cat_a_state["message"] = f"ADB error: {e}"
        print(f"❌ Device detection error: {e}")

# =====================================================
# DEVICE MONITOR THREAD (RUN ONCE)
# =====================================================

def start_device_monitor():
    def _monitor():
        while True:
            detect_devices()
            time.sleep(2)

    threading.Thread(target=_monitor, daemon=True).start()


# =====================================================
# PAUSE/RESUME CONTROL FUNCTIONS
# =====================================================

def pause_test():
    """Pause the running test"""
    if cat_a_state["state"] == "RUNNING":
        cat_a_state["paused"] = True
        cat_a_state["state"] = "PAUSED"
        cat_a_state["message"] = "Test paused by user"
        print("⏸️ TEST PAUSED")
        return {"status": "success", "message": "Test paused"}
    else:
        return {"status": "error", "message": "No test is running"}

def resume_test():
    """Resume the paused test"""
    if cat_a_state["state"] == "PAUSED":
        cat_a_state["paused"] = False
        cat_a_state["state"] = "RUNNING"
        cat_a_state["message"] = "Test resumed"
        print("▶️ TEST RESUMED")
        return {"status": "success", "message": "Test resumed"}
    else:
        return {"status": "error", "message": "Test is not paused"}

def stop_test():
    """Stop the running test"""
    if cat_a_state["state"] in ["RUNNING", "PAUSED"]:
        cat_a_state["stop_requested"] = True
        cat_a_state["state"] = "STOPPED"
        cat_a_state["message"] = "Test stopped by user"
        print("⏹️ TEST STOPPED")
        return {"status": "success", "message": "Test stopped"}
    else:
        return {"status": "error", "message": "No test is running"}

def clear_disconnect_alert():
    """Clear device disconnection alert"""
    cat_a_state["device_disconnected"] = False
    cat_a_state["disconnected_device"] = None
    return {"status": "success", "message": "Alert cleared"}


# =====================================================
# CAT-A SERVICE STARTER (WITH PAUSE/RESUME SUPPORT)
# =====================================================

def start_cat_a_service(config: dict):
    """
    UI → Service → Runner → Existing CAT-A automation
    Now with pause/resume support
    """

    def _run():
        try:
            print("✅ CAT-A SERVICE STARTED")
            print("CONFIG FROM UI:", config)

            # Reset pause/stop flags
            cat_a_state["paused"] = False
            cat_a_state["stop_requested"] = False
            cat_a_state["device_disconnected"] = False
            cat_a_state["disconnected_device"] = None
            cat_a_state["test_running"] = True

            # ===============================
            # HARD SAFETY GUARDS
            # ===============================

            if not cat_a_state["mo_connected"]:
                cat_a_state["state"] = "FAILED"
                cat_a_state["message"] = "MO device not connected"
                cat_a_state["test_running"] = False
                print("❌ MO NOT CONNECTED")
                return

            if not cat_a_state["mt_connected"]:
                cat_a_state["state"] = "FAILED"
                cat_a_state["message"] = "MT device not connected"
                cat_a_state["test_running"] = False
                print("❌ MT NOT CONNECTED")
                return

            if not config.get("mt_number"):
                cat_a_state["state"] = "FAILED"
                cat_a_state["message"] = "MT phone number not saved"
                cat_a_state["test_running"] = False
                print("❌ MT NUMBER MISSING")
                return

            # ===============================
            # 🔑 CORRECT CONFIG MAPPING
            # (MATCHES legacy CAT-A code)
            # ===============================
            
            if not cat_a_state.get("mo_serial") or not cat_a_state.get("mt_serial"):
                cat_a_state["state"] = "FAILED"
                cat_a_state["message"] = "MO/MT serial not available"
                cat_a_state["test_running"] = False
                return

            mapped_config = {
                "test_type": config["test_type"],           # REQUIRED
                "mt_number": config["mt_number"],
                "iterations": config["iterations"],
                "call_duration": config["call_duration"],
                "call_delay": config["call_delay"],

                # pull from shared runtime state
                "mo_serial": cat_a_state["mo_serial"],
                "mt_serial": cat_a_state["mt_serial"],
            }

            # Store total iterations for progress tracking
            cat_a_state["total_iterations"] = config["iterations"]
            cat_a_state["current_iteration"] = 0

            print("MAPPED CONFIG:", mapped_config)

            # ===============================
            # START EXECUTION
            # ===============================

            cat_a_state["state"] = "RUNNING"
            cat_a_state["message"] = "CAT-A execution started"
            cat_a_state["progress"] = 0

            # 🔥 ACTUAL AUTOMATION (with pause/resume support passed via cat_a_state)
            start_cat_a_test(mapped_config)

            # Only mark as completed if not stopped
            if not cat_a_state.get("stop_requested", False):
                cat_a_state["state"] = "COMPLETED"
                cat_a_state["message"] = "CAT-A execution completed"
                cat_a_state["progress"] = 100

            cat_a_state["test_running"] = False
            print("✅ CAT-A EXECUTION FINISHED")

        except Exception as e:
            cat_a_state["state"] = "FAILED"
            cat_a_state["message"] = str(e)
            cat_a_state["test_running"] = False
            print("❌ CAT-A ERROR:", e)

    threading.Thread(target=_run, daemon=True).start()
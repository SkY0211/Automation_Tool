import threading
import subprocess
import time

from backend.cat_a_tool.runner import start_cat_a_test

# =====================================================
# CAT-A shared runtime state (SINGLE SOURCE OF TRUTH)
# =====================================================

cat_a_state = {
    "state": "IDLE",
    "message": "",
    "progress": 0,

    # Backward compatible (pair 1)
    "mo_connected": False,
    "mt_connected": False,
    "mo_serial": None,
    "mt_serial": None,

    "connection_order": [],

    # NEW: multi-device support
    "devices": [],
    "pairs": [],
    
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
    """
    devices = cat_a_state.get("devices", [])

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
    """
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )

        lines = result.stdout.strip().split("\n")[1:]
        current_devices = [line.split()[0] for line in lines if "device" in line]

        if "connection_order" not in cat_a_state:
            cat_a_state["connection_order"] = []
        
        existing_order = cat_a_state["connection_order"]
        
        # ✅ CRITICAL: Device disconnection detection ONLY during active test
        test_is_running = cat_a_state.get("test_running", False)
        
        if test_is_running:
            mo_serial = cat_a_state.get("mo_serial")
            mt_serial = cat_a_state.get("mt_serial")
            
            # Check MO disconnection
            if mo_serial and mo_serial not in current_devices:
                if not cat_a_state.get("device_disconnected", False):
                    cat_a_state["device_disconnected"] = True
                    cat_a_state["disconnected_device"] = "MO"
                    cat_a_state["paused"] = True  # PAUSE test (not stop)
                    cat_a_state["state"] = "PAUSED"
                    print(f"⚠️ ALERT: MO device {mo_serial} disconnected during test - TEST PAUSED!")
                    
            # Check MT disconnection
            if mt_serial and mt_serial not in current_devices:
                if not cat_a_state.get("device_disconnected", False):
                    cat_a_state["device_disconnected"] = True
                    cat_a_state["disconnected_device"] = "MT"
                    cat_a_state["paused"] = True  # PAUSE test (not stop)
                    cat_a_state["state"] = "PAUSED"
                    print(f"⚠️ ALERT: MT device {mt_serial} disconnected during test - TEST PAUSED!")
        
        # If NO devices connected, clear everything
        if not current_devices:
            cat_a_state["connection_order"] = []
            cat_a_state["devices"] = []
            cat_a_state["mo_serial"] = None
            cat_a_state["mt_serial"] = None
            cat_a_state["mo_connected"] = False
            cat_a_state["mt_connected"] = False
            cat_a_state["pairs"] = []
            
            # Don't trigger disconnect alert if no test is running
            if not test_is_running:
                cat_a_state["device_disconnected"] = False
                cat_a_state["disconnected_device"] = None
            
            print("🔍 DEVICE DETECTION: NO DEVICES CONNECTED - STATE CLEARED")
            return
        
        # Update connection order
        existing_order = [d for d in existing_order if d in current_devices]
        
        for device in current_devices:
            if device not in existing_order:
                existing_order.append(device)
        
        cat_a_state["connection_order"] = existing_order
        devices = cat_a_state["connection_order"]
        
        cat_a_state["devices"] = devices
        cat_a_state["mo_serial"] = devices[0] if len(devices) >= 1 else None
        cat_a_state["mt_serial"] = devices[1] if len(devices) >= 2 else None

        update_pairs_from_devices()

        cat_a_state["mo_connected"] = cat_a_state["mo_serial"] is not None
        cat_a_state["mt_connected"] = cat_a_state["mt_serial"] is not None
        
        # Only print full details every 10 seconds to reduce spam
        if not hasattr(detect_devices, 'counter'):
            detect_devices.counter = 0
        detect_devices.counter += 1
        
        if detect_devices.counter % 5 == 0:  # Every 10 seconds (since it runs every 2s)
            print(f"🔍 DEVICE DETECTION:")
            print(f"   Connection order: {devices}")
            print(f"   MO = {cat_a_state['mo_serial']} (Connected: {cat_a_state['mo_connected']})")
            print(f"   MT = {cat_a_state['mt_serial']} (Connected: {cat_a_state['mt_connected']})")
            if test_is_running:
                print(f"   ⚠️ TEST RUNNING - Monitoring for disconnections")

    except Exception as e:
        cat_a_state["mo_connected"] = False
        cat_a_state["mt_connected"] = False
        cat_a_state["mo_serial"] = None
        cat_a_state["mt_serial"] = None
        cat_a_state["devices"] = []
        cat_a_state["pairs"] = []
        cat_a_state["message"] = f"ADB error: {e}"
        
        if not cat_a_state.get("test_running", False):
            cat_a_state["device_disconnected"] = False
            cat_a_state["disconnected_device"] = None
            
        print(f"❌ Device detection error: {e}")

# =====================================================
# DEVICE MONITOR THREAD (RUN ONCE)
# =====================================================

def start_device_monitor():
    """Start background thread to monitor devices"""
    def _monitor():
        time.sleep(3)
        
        cat_a_state["device_disconnected"] = False
        cat_a_state["disconnected_device"] = None
        print("=" * 60)
        print("✅ Device monitor started - all flags cleared")
        print("📱 Connect your devices NOW in order: MO first, then MT")
        print("=" * 60)
        
        while True:
            detect_devices()
            time.sleep(2)

    threading.Thread(target=_monitor, daemon=True).start()


# =====================================================
# PAUSE/RESUME CONTROL FUNCTIONS
# =====================================================

def pause_test():
    """Pause the running test"""
    if cat_a_state["state"] == "RUNNING" and cat_a_state.get("test_running", False):
        cat_a_state["paused"] = True
        cat_a_state["state"] = "PAUSED"
        cat_a_state["message"] = "Test paused by user"
        print("⏸️ TEST PAUSED")
        return {"status": "success", "message": "Test paused"}
    else:
        return {"status": "error", "message": "No test is running"}


def resume_test():
    """Resume the paused test"""
    if cat_a_state["state"] == "PAUSED" and cat_a_state.get("test_running", False):
        cat_a_state["paused"] = False
        cat_a_state["state"] = "RUNNING"
        cat_a_state["message"] = "Test resumed"
        print("▶️ TEST RESUMED")
        return {"status": "success", "message": "Test resumed"}
    else:
        return {"status": "error", "message": "Test is not paused"}

def stop_test():
    """Stop the running test"""
    if cat_a_state.get("test_running", False):
        cat_a_state["stop_requested"] = True
        cat_a_state["state"] = "STOPPED"
        cat_a_state["message"] = "Test stopped by user"
        cat_a_state["test_running"] = False
        
        cat_a_state["device_disconnected"] = False
        cat_a_state["disconnected_device"] = None
        
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
    """

    def _run():
        try:
            print("=" * 60)
            print("✅ CAT-A SERVICE STARTED")
            print("=" * 60)

            # ✅ CRITICAL: Set test_running FIRST
            cat_a_state["test_running"] = True
            cat_a_state["paused"] = False
            cat_a_state["stop_requested"] = False
            cat_a_state["device_disconnected"] = False
            cat_a_state["disconnected_device"] = None
            
            print("🔒 Test started: test_running = TRUE")

            # Safety guards
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

            if not cat_a_state.get("mo_serial") or not cat_a_state.get("mt_serial"):
                cat_a_state["state"] = "FAILED"
                cat_a_state["message"] = "MO/MT serial not available"
                cat_a_state["test_running"] = False
                return

            mapped_config = {
                "test_type": config["test_type"],
                "mt_number": config["mt_number"],
                "iterations": config["iterations"],
                "call_duration": config["call_duration"],
                "call_delay": config["call_delay"],
                "mo_serial": cat_a_state["mo_serial"],
                "mt_serial": cat_a_state["mt_serial"],
            }

            cat_a_state["total_iterations"] = config["iterations"]
            cat_a_state["current_iteration"] = 0
            cat_a_state["state"] = "RUNNING"
            cat_a_state["message"] = "CAT-A execution started"
            cat_a_state["progress"] = 0

            print(f"📱 Using MO: {cat_a_state['mo_serial']}")
            print(f"📱 Using MT: {cat_a_state['mt_serial']}")
            print("=" * 60)

            # ✅ CRITICAL: Start test (this runs in background thread)
            start_cat_a_test(mapped_config)

            # ✅ IMPORTANT: Don't set test_running = False here!
            # The test is still running in the background thread
            # It will be set to False when:
            # 1. Test completes naturally (in progress checker)
            # 2. User stops test (in stop_test())
            # 3. Device disconnects (in detect_devices())
            
            print("✅ TEST FINISHED: test_running = FALSE")
            print("=" * 60)

        except Exception as e:
            cat_a_state["state"] = "FAILED"
            cat_a_state["message"] = str(e)
            cat_a_state["test_running"] = False
            
            cat_a_state["device_disconnected"] = False
            cat_a_state["disconnected_device"] = None
            
            print("=" * 60)
            print("❌ CAT-A ERROR:", e)
            print("=" * 60)

    threading.Thread(target=_run, daemon=True).start()
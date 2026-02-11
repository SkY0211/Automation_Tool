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

    "connection_order": [],      # ← ADD THIS LINE

    # NEW: multi-device support
    "devices": [],               # raw adb list
    "pairs": []                  # derived MO–MT pairs
}

def update_pairs_from_devices():
    """
    UI helper: derive MO–MT pairs from connected devices
    Does NOT change automation logic
    """
    devices = cat_a_state.get("devices", [])

    cat_a_state["pairs"] = {}

    pair_index = 1
    for i in range(0, len(devices), 2):
        mo = devices[i] if i < len(devices) else None
        mt = devices[i + 1] if i + 1 < len(devices) else None

        cat_a_state["pairs"][pair_index] = {
            "mo": {
                "name": f"MO{pair_index}",
                "connected": bool(mo)
            },
            "mt": {
                "name": f"MT{pair_index}",
                "connected": bool(mt)
            }
        }

        pair_index += 1


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
            text=True
        )

        lines = result.stdout.strip().split("\n")[1:]
        current_devices = [line.split()[0] for line in lines if "device" in line]

        # 🔧 FIX: Maintain connection order
        # Initialize connection_order if it doesn't exist
        if "connection_order" not in cat_a_state:
            cat_a_state["connection_order"] = []
        
        existing_order = cat_a_state["connection_order"]
        
        # Remove disconnected devices from order
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

        update_pairs_from_devices()

        cat_a_state["mo_connected"] = cat_a_state["mo_serial"] is not None
        cat_a_state["mt_connected"] = cat_a_state["mt_serial"] is not None
        
        # 🔍 DEBUG LOGGING
        print(f"🔍 DEVICE DETECTION:")
        print(f"   Current ADB devices (alphabetical): {current_devices}")
        print(f"   Connection order (preserved): {devices}")
        print(f"   MO = {cat_a_state['mo_serial']}")
        print(f"   MT = {cat_a_state['mt_serial']}")

    except Exception as e:
        cat_a_state["mo_connected"] = False
        cat_a_state["mt_connected"] = False
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
# CAT-A SERVICE STARTER (FINAL + CORRECT)
# =====================================================

def start_cat_a_service(config: dict):
    """
    UI → Service → Runner → Existing CAT-A automation
    """

    def _run():
        try:
            print(" CAT-A SERVICE STARTED")
            print("CONFIG FROM UI:", config)

            # ===============================
            # HARD SAFETY GUARDS
            # ===============================

            if not cat_a_state["mo_connected"]:
                cat_a_state["state"] = "FAILED"
                cat_a_state["message"] = "MO device not connected"
                print(" MO NOT CONNECTED")
                return

            if not cat_a_state["mt_connected"]:
                cat_a_state["state"] = "FAILED"
                cat_a_state["message"] = "MT device not connected"
                print(" MT NOT CONNECTED")
                return

            if not config.get("mt_number"):
                cat_a_state["state"] = "FAILED"
                cat_a_state["message"] = "MT phone number not saved"
                print(" MT NUMBER MISSING")
                return

            # ===============================
            # 🔑 CORRECT CONFIG MAPPING
            # (MATCHES legacy CAT-A code)
            # ===============================
            
            if not cat_a_state.get("mo_serial") or not cat_a_state.get("mt_serial"):
                cat_a_state["state"] = "FAILED"
                cat_a_state["message"] = "MO/MT serial not available"
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


            print("MAPPED CONFIG:", mapped_config)

            # ===============================
            # START EXECUTION
            # ===============================

            cat_a_state["state"] = "RUNNING"
            cat_a_state["message"] = "CAT-A execution started"
            cat_a_state["progress"] = 0

            #  ACTUAL AUTOMATION
            start_cat_a_test(mapped_config)

            cat_a_state["state"] = "COMPLETED"
            cat_a_state["message"] = "CAT-A execution completed"
            cat_a_state["progress"] = 100

            print(" CAT-A EXECUTION FINISHED")

        except Exception as e:
            cat_a_state["state"] = "FAILED"
            cat_a_state["message"] = str(e)
            print(" CAT-A ERROR:", e)

    threading.Thread(target=_run, daemon=True).start()

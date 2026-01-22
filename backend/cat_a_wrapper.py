from backend.cat_a_tool.automate_call import run_automation

def run_cat_a_tool(config: dict):
    return run_automation(config)

    config = {
        "simulate": False,          # 🔥 critical
        "home": None,               # PyQt, not Tk
        "all_device_info": {},      # backend will auto-detect
        "phone_numbers": [],
        "pair_widgets": [],
        "test_type": "Short calls",
        "iterations": 5,
        "call_duration": 30,
        "call_delay": 5,
        "device_count": 2           # 🔥 YOU HAVE 2 DEVICES
    }

    print("🔥 REAL CAT-A BACKEND STARTED 🔥")
    result = run_automation(config)
    print("🔥 REAL CAT-A BACKEND FINISHED 🔥")

    return result

from backend.cat_a_tool.automate_call import run_automation

def start_cat_a_test(config):
    print("🔥 REAL CAT-A BACKEND STARTED 🔥")
    result = run_automation(config)
    print("🔥 REAL CAT-A BACKEND FINISHED 🔥")
    return result

from backend.cat_a_tool.automate_call import CallTester
from backend.cat_a_tool.logger import CustomLogger
import threading
import queue


def start_cat_a_test(config):
    logger = CustomLogger("CAT_A_RUNNER")

    try:
        logger.log("start_cat_a_test ENTERED")
        logger.log(f"CONFIG RECEIVED: {config}")

        # -------------------------------------------------
        # Normalize call duration (SECONDS SAFETY FIX)
        # -------------------------------------------------
        call_duration = int(config["call_duration"])

        # If UI accidentally sends minutes (1, 2, 5), convert to seconds
        if call_duration <= 10:
            logger.log(
                f"call_duration looks like minutes ({call_duration}), converting to seconds"
            )
            call_duration = call_duration * 60

        logger.log(f"FINAL call_duration USED (seconds): {call_duration}")

        q = queue.Queue()

        tester = CallTester(
            home=None,
            cred_mo={"udid": config["mo_serial"], "Sim_Preference": 0},
            cred_mt={"udid": config["mt_serial"], "Sim_Preference": 0},
            test_type="Short calls" if config["test_type"] == "short" else "Long calls",
            iterations=int(config["iterations"]),
            call_duration=call_duration,        # ✅ FIXED
            call_delay=int(config["call_delay"]),
            ph_no=config["mt_number"],
            frame=None,
            mo_label="MO",
            mt_label="MT",
            barriers=[
                threading.Barrier(1),  # single MO–MT pair
                threading.Barrier(1),
                threading.Barrier(1)
            ],
            no_of_devices=1
        )
        
        # Store this run's unique test_id in the tester
        tester.my_test_id = config.get("test_id", 0)

        logger.log("CallTester initialized successfully")

        # -------------------------------------------------
        # Start automation in background thread
        # -------------------------------------------------
        t = threading.Thread(
            target=tester.run_test,
            args=(q,),
            daemon=True        # ✅ IMPORTANT
        )
        t.start()

        logger.log("CAT-A automation thread started")

        # ❌ DO NOT JOIN — Flask must stay responsive
        # t.join()

    except Exception as e:
        logger.log(f"CAT-A RUNNER ERROR: {e}")
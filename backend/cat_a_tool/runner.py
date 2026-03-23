from backend.cat_a_tool.automate_call import CallTester
from backend.cat_a_tool.logger import CustomLogger
import threading
import queue


def start_cat_a_test(pair_configs):
    """
    Accepts a list of pair configs (one per MO-MT pair).
    Spins up one CallTester thread per pair, all running concurrently.
    Progress reflects the slowest pair. running=False only after ALL pairs finish.
    """
    logger = CustomLogger("CAT_A_RUNNER")

    try:
        logger.log("start_cat_a_test ENTERED")
        logger.log(f"Number of pairs: {len(pair_configs)}")

        num_pairs = len(pair_configs)

        threads = []

        # ✅ Per-pair progress tracking (for multi-pair mode)
        pair_progress = {}  # pair_id -> current iteration count
        progress_lock = threading.Lock()

        def make_progress_callback(pair_id, total_itr):
            def callback(current):
                from backend.cat_a_tool.progress_state import progress_data
                with progress_lock:
                    pair_progress[pair_id] = current
                    # Progress = minimum across all pairs (slowest pair drives the bar)
                    min_current = min(pair_progress.values())
                    progress_data["current"] = min_current
                    progress_data["percent"] = int((min_current / total_itr) * 100)
            return callback

        for config in pair_configs:
            logger.log(f"CONFIG for Pair {config['pair_id']}: {config}")

            call_duration = config["call_duration"] * 60
            logger.log(f"FINAL call_duration USED (seconds): {call_duration}")

            q = queue.Queue()
            total_itr = int(config["iterations"])

            # ✅ Each pair gets its own independent barriers (size=1)
            # Pairs run fully independently — no cross-pair synchronisation needed
            pair_barriers = [
                threading.Barrier(1),
                threading.Barrier(1),
                threading.Barrier(1)
            ]

            tester = CallTester(
                home=None,
                cred_mo={"udid": config["mo_serial"], "Sim_Preference": 0},
                cred_mt={"udid": config["mt_serial"], "Sim_Preference": 0},
                test_type="Short calls" if config["test_type"] == "short" else "Long calls",
                iterations=total_itr,
                call_duration=call_duration,
                call_delay=int(config["call_delay"]),
                ph_no=config["mt_number"],
                frame=None,
                mo_label=config.get("mo_label", f"MO{config['pair_id']}"),
                mt_label=config.get("mt_label", f"MT{config['pair_id']}"),
                barriers=pair_barriers,
                no_of_devices=1
            )

            tester.my_test_id = config.get("test_id", 0)

            if num_pairs > 1:
                pair_id = config["pair_id"]
                pair_progress[pair_id] = 0
                tester._multi_pair_mode = True
                tester._pair_progress_callback = make_progress_callback(pair_id, total_itr)

            logger.log(f"CallTester initialized for Pair {config['pair_id']}")

            t = threading.Thread(
                target=tester.run_test,
                args=(q,),
                daemon=True
            )
            threads.append(t)

        # Start all pair threads concurrently
        for t in threads:
            t.start()

        logger.log(f"✅ {num_pairs} CAT-A pair thread(s) started")

        # ✅ Coordinator: wait for ALL pairs to finish, then mark complete
        if num_pairs > 1:
            def _coordinator():
                from backend.cat_a_tool.progress_state import progress_data
                logger.log("⏳ Coordinator waiting for all pairs to finish...")
                for t in threads:
                    t.join()
                logger.log("✅ All pairs finished — marking progress complete")
                progress_data["current"] = progress_data.get("total", 0)
                progress_data["percent"] = 100
                progress_data["running"] = False

            threading.Thread(target=_coordinator, daemon=True).start()

    except Exception as e:
        logger.log(f"CAT-A RUNNER ERROR: {e}")